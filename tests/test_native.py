import pytest
from powermanager import native
from powermanager.model import table_controls, Snapshot


def test_table_parsing_uses_cells_not_stale_hidden_gauges():
    rows = [
        ["Входное напряжение", "229.00", "В", "Выходное напряжение", "230.00", "В"],
        ["Заряд батарей", "70", "%", "Входная частота", "50.00", "Гц"],
        ["Нагрузка на ИБП", "15", "%", "Температура", "21.00", "°C"],
        ["Индикатор подключение ИБП", "ИБП подключен", "", "", "", ""],
    ]
    controls = table_controls(rows, "PowerManager")
    assert controls[1002] == "229.00"
    assert controls[1038] == "50.00"
    assert controls[1039] == "15"
    assert Snapshot.from_controls(controls).connected is True


def test_missing_table_connection_is_not_assumed_connected():
    controls = table_controls([["Input Voltage", "234", "V"]], "PowerManager")
    assert Snapshot.from_controls(controls).connected is None


def test_unknown_command_never_posts(monkeypatch):
    posted = []
    monkeypatch.setattr(native.u, "PostMessageW", lambda *a: posted.append(a))
    with pytest.raises(KeyError):
        native.Backend(1).command("arbitrary-device-command")
    assert posted == []


def test_modal_blocks_command_dispatch(monkeypatch):
    backend = native.Backend(1)
    monkeypatch.setattr(backend, "main", lambda: 100)
    monkeypatch.setattr(backend, "windows", lambda: [100, 101])
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: True)
    posted = []
    monkeypatch.setattr(native.u, "PostMessageW", lambda *a: posted.append(a))
    with pytest.raises(native.Unavailable):
        backend.command("settings")
    assert posted == []


def test_dead_window_cannot_be_activated(monkeypatch):
    monkeypatch.setattr(native.u, "IsWindow", lambda h: False)
    with pytest.raises(native.Unavailable):
        native.Backend(1).validate_control(55)


def test_foreign_process_cannot_be_activated(monkeypatch):
    monkeypatch.setattr(native.u, "IsWindow", lambda h: True)
    monkeypatch.setattr(native, "process_id", lambda h: 999)
    with pytest.raises(native.Unavailable):
        native.Backend(1).validate_control(55)


def test_timeout_is_reported(monkeypatch):
    monkeypatch.setattr(native.u, "SendMessageTimeoutW", lambda *a: 0)
    with pytest.raises(native.Unavailable):
        native.send(55, 0)


def test_graph_mode_does_not_return_stale_gauges(monkeypatch):
    backend = native.Backend(1)
    monkeypatch.setattr(backend, "main", lambda: 100)
    monkeypatch.setattr(native, "send", lambda *a: 0)
    monkeypatch.setattr(native.u, "GetDlgItem", lambda h, cid: cid)
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: False)
    with pytest.raises(native.Unavailable, match="графика"):
        backend.snapshot()


def test_visible_table_calls_provider(monkeypatch):
    called = []

    def provider(hwnd):
        called.append(hwnd)
        return [["UPS Connect indication", "UPS Disconnected", ""]]

    backend = native.Backend(1, provider)
    monkeypatch.setattr(backend, "main", lambda: 100)
    monkeypatch.setattr(native, "send", lambda *a: 0)
    monkeypatch.setattr(native.u, "GetDlgItem", lambda h, cid: cid)
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: h == 1034)
    monkeypatch.setattr(native, "window_text", lambda h: "PowerManager")
    result = backend.snapshot()
    assert called == [1034]
    assert result.connected is False
