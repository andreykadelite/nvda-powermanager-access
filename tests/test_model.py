from datetime import datetime
import pytest
from powermanager.model import Snapshot, ChangeTracker, COMMANDS, numeric_value, MAIN_SIGNATURE
from powermanager.labels import label_for, match_template


def sample(state="ИБП подключен", **kwargs):
    controls = {
        1023: state,
        1024: "Напряжение в норме",
        1025: "Батарея в норме",
        1026: "ИБП в норме",
        1027: "Тест не запущен",
        1028: "Инвертор",
        1002: "234.0",
        1037: "233.0",
        1038: "50.0",
        1039: " 9.0",
        1042: "100%",
    }
    controls.update({int(k): v for k, v in kwargs.items()})
    return Snapshot.from_controls(controls, datetime(2026, 9, 6, 12, 0, 0))


def test_live_values_have_units():
    data = sample()
    assert data.connected is True
    assert data.metrics == (
        ("Входное напряжение", "234,0 В"),
        ("Входная частота", "50,0 Гц"),
        ("Выходное напряжение", "233,0 В"),
        ("Нагрузка", "9,0 %"),
        ("Заряд батареи", "100 %"),
    )
    assert "12:00:00" in data.report()


@pytest.mark.parametrize("state", ["UPS Disconnected", "ИБП отключен", "ИБП отсоединён", "Нет связи"])
def test_disconnect_never_reports_cached_voltage_as_current(state):
    data = sample(state)
    assert data.connected is False
    assert all(value == "нет подтверждённых данных" for _, value in data.metrics)
    assert "234" not in data.report()


@pytest.mark.parametrize("state", ["", "Неизвестно", "Unbekannt"])
def test_unknown_connection_is_not_assumed_healthy(state):
    assert sample(state).connected is None
    assert "234" not in sample(state).report()


@pytest.mark.parametrize("text", ["", "---", "nan", "inf", "2e5", "100V", "<script>", "1.2.3"])
def test_invalid_numeric_values(text):
    assert numeric_value(text, "В") == "нет данных"


def test_zero_is_a_reading_not_missing_data():
    assert numeric_value("0", "%") == "0 %"


def test_monitor_announces_only_status_transitions():
    tracker = ChangeTracker()
    assert tracker.update(sample()) == ()
    assert tracker.update(sample(**{"1002": "229.0"})) == ()
    assert tracker.update(sample(**{"1024": "Работа от батареи"})) == ("Работа от батареи",)
    assert tracker.update(sample(**{"1024": "Работа от батареи"})) == ()


def test_monitor_reports_reconnection():
    tracker = ChangeTracker()
    tracker.update(sample())
    assert tracker.update(sample("ИБП отключен")) == ("ИБП отключен",)
    assert tracker.update(sample()) == ("ИБП подключен",)


def test_command_map_has_unique_verified_ids():
    assert len({c.key for c in COMMANDS}) == len(COMMANDS)
    assert len({c.command_id for c in COMMANDS}) == len(COMMANDS)
    assert all(c.confirm for c in COMMANDS if c.key in {"clear", "beeper"})


def test_main_button_label_does_not_leak_to_other_dialog():
    assert label_for(MAIN_SIGNATURE, 1009, "Button", "") == "Настройки системы"
    assert label_for({1009, 1, 2}, 1009, "Button", "Флажок") == "Флажок"


def test_unknown_dialog_preserves_names():
    assert match_template({8, 9, 10}) is None
    assert label_for({8, 9, 10}, 9, "Edit", "My label") == "My label"
