from powermanager.views import state_items, measurement_items, VIEW_KEYS, VIEW_BY_ID
from powermanager.model import Snapshot
from powermanager import native


def test_measurements_preserve_both_column_groups_and_units():
    rows = [
        ["Входное напряжение", "0", "В", "Температура", "20.80", "°C"],
        ["Напряжение батарей", "Батареи в норме", "", "Напряжение батарей", "27.00", "В"],
    ]
    assert measurement_items(rows, True) == [
        "Входное напряжение: 0 В",
        "Температура: 20,80 °C",
        "Состояние батареи: Батареи в норме",
        "Напряжение батареи: 27,00 В",
    ]


def test_disconnected_readings_are_not_presented_as_current():
    rows = [["Входное напряжение", "234", "В", "Индикатор подключение ИБП", "ИБП отключен", ""]]
    items = measurement_items(rows, False)
    assert "234" not in "\n".join(items)
    assert items[-1] == "Связь с ИБП: ИБП отключен"


def test_empty_and_invalid_measurement_rows_remain_readable():
    assert "не передала" in measurement_items([], True)[0]
    assert measurement_items([["Температура", "nan", "°C"]], True) == ["Температура: нет данных"]
    assert len(measurement_items([["Наименование сигнала", "", "", "Температура", "21", "°C"]], True)) == 1
    assert measurement_items(
        [["Наименование сигнала", "Показания", "Ед.измерения"]], True
    ) == measurement_items([], True)


def test_state_tab_has_explicit_signal_labels():
    snapshot = Snapshot.from_controls({1023: "ИБП подключен", 1027: "Отмена самотеста", 1042: "0", 1039: "0"})
    items = state_items(snapshot)
    assert "Самотестирование: не выполняется" in items
    assert "Заряд батареи: 0 %" in items
    assert "Связь с ИБП: ИБП подключен" in items


def test_main_views_have_one_stable_order():
    assert VIEW_KEYS == ("status", "table", "curve")
    assert {v.key for v in VIEW_BY_ID.values()} == set(VIEW_KEYS)


def test_current_view_is_observed_not_remembered(monkeypatch):
    backend = native.Backend(1)
    monkeypatch.setattr(backend, "main", lambda: 100)
    monkeypatch.setattr(native.u, "GetDlgItem", lambda root, cid: cid)
    visible = {1034}
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: h in visible)
    monkeypatch.setattr(native, "children", lambda root: [55])
    monkeypatch.setattr(native, "class_name", lambda h: "AfxOleControl42")
    assert backend.current_view() == "table"
    visible.clear()
    visible.add(1002)
    assert backend.current_view() == "status"
    visible.clear()
    visible.add(55)
    assert backend.current_view() == "curve"
    visible.clear()
    assert backend.current_view() is None
