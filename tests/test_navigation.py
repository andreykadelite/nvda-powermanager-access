import pytest
from powermanager import native
from powermanager.labels import TEMPLATES, match_template, label_for, RADIO_GROUPS


def test_identical_delete_templates_have_identical_safe_names():
    for t in TEMPLATES:
        if t["key"] in {"PMConfig.dll_5_143_1033", "PowerManager.exe_5_143_1033"}:
            assert match_template(t["ids"]) is not None
            assert label_for(t["ids"], 1037, "SysDateTimePick32", "") == "Начальная дата удаления"
            assert label_for(t["ids"], 1, "Button", "") == "Удалить выбранные записи"


def test_radio_group_tab_never_focuses_unselected_power_action(monkeypatch):
    template = next(t for t in TEMPLATES if t["key"] == "PowerManager.exe_5_16007_1033")
    items = [16014, 16025, 16015, 16018, 16021, 16023, 1, 2]
    monkeypatch.setattr(native, "process_id", lambda h: 1)
    monkeypatch.setattr(native, "children", lambda h, **kwargs: items)
    monkeypatch.setattr(native, "class_name", lambda h: "Edit" if h in (16018, 16021, 16023) else "Button")
    monkeypatch.setattr(native, "control_ids", lambda h: frozenset(template["ids"]))
    monkeypatch.setattr(native, "is_main", lambda h: False)
    monkeypatch.setattr(native.u, "GetDlgCtrlID", lambda h: h)
    monkeypatch.setattr(native.u, "GetParent", lambda h: 100)
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: True)
    monkeypatch.setattr(native.u, "IsWindowEnabled", lambda h: h not in (16018,))
    monkeypatch.setattr(native.u, "GetWindowLongW", lambda *a: 0)
    monkeypatch.setattr(native, "send", lambda h, *a: 1 if h == 16025 else 0)
    controls = native.Backend(1).visible_controls(100)
    assert controls == [16025, 16021, 16023, 1, 2]
    assert all(
        h in native.Backend(1).visible_controls(100, include_disabled=True)
        for h in RADIO_GROUPS[template["key"]][0]
    )


def test_child_in_disabled_owner_cannot_receive_action(monkeypatch):
    monkeypatch.setattr(native.u, "IsWindow", lambda h: True)
    monkeypatch.setattr(native, "process_id", lambda h: 1)
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: True)
    monkeypatch.setattr(native.u, "GetAncestor", lambda *a: 100)
    monkeypatch.setattr(native.u, "IsWindowEnabled", lambda h: h != 100)
    with pytest.raises(native.Unavailable, match="заблокировано"):
        native.Backend(1).validate_control(2)


def test_settings_headers_are_one_tab_stop_but_all_remain_in_element_panel(monkeypatch):
    template = next(t for t in TEMPLATES if t["key"] == "PMConfig.dll_5_101_1033")
    monkeypatch.setattr(native, "process_id", lambda h: 1)
    monkeypatch.setattr(native, "children", lambda h, **kwargs: [3, 4, 5, 6, 1062, 1, 2])
    monkeypatch.setattr(native, "class_name", lambda h: "Button")
    monkeypatch.setattr(native, "control_ids", lambda h: frozenset(template["ids"]))
    monkeypatch.setattr(native, "is_main", lambda h: False)
    monkeypatch.setattr(native, "active_section", lambda *args: 6)
    monkeypatch.setattr(native, "send", lambda *args: 0)
    monkeypatch.setattr(native.u, "GetDlgCtrlID", lambda h: h)
    monkeypatch.setattr(native.u, "GetParent", lambda h: 100)
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: True)
    monkeypatch.setattr(native.u, "IsWindowEnabled", lambda h: True)
    monkeypatch.setattr(native.u, "GetWindowLongW", lambda *a: 0)
    controls = native.Backend(1).visible_controls(100)
    assert controls[0] == 6 and set(controls) == {6, 1062, 1, 2}
    assert {3, 4, 5, 6} <= set(native.Backend(1).visible_controls(100, include_disabled=True))
