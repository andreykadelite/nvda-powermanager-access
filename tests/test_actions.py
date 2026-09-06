"""Exercise the actual AppModule action gates without NVDA, a UPS, or UI messages."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace, ModuleType
import sys
import pytest
from powermanager import native
from powermanager.labels import TEMPLATES


@pytest.fixture
def app(monkeypatch):
    def module(name, **items):
        value = ModuleType(name)
        value.__dict__.update(items)
        monkeypatch.setitem(sys.modules, name, value)
        return value

    for name in ("api", "core", "controlTypes", "gui", "ui", "wx", "winUser", "inputCore", "NVDAObjects"):
        module(name)
    module("appModuleHandler", AppModule=object)
    module("logHandler", log=SimpleNamespace(debugWarning=lambda *a, **kw: None))
    module("NVDAObjects.IAccessible", IAccessible=object, getNVDAObjectFromEvent=lambda *a: None)
    module("scriptHandler", script=lambda **kw: lambda func: func)
    path = Path(__file__).resolve().parents[1] / "addon/appModules/powermanager/__init__.py"
    spec = importlib.util.spec_from_file_location(
        "powermanager.test_entry", path, submodule_search_locations=None
    )
    entry = importlib.util.module_from_spec(spec)
    entry.__package__ = "powermanager"
    spec.loader.exec_module(entry)
    instance = object.__new__(entry.AppModule)
    return instance


def prepare(app, monkeypatch, template_key, cid):
    validated, posted, confirmation = [], [], []
    app.backend = SimpleNamespace(
        validate_control=lambda h: validated.append(h), selected_row=lambda *a: False
    )
    app._last_activation = (0, 0)
    app.selection_summary = lambda root: "Тестовые параметры"
    app.confirm_action = lambda prompt, action: confirmation.append((prompt, action))
    template = next(t for t in TEMPLATES if t["key"] == template_key)
    monkeypatch.setattr(native.u, "GetAncestor", lambda *a: 1000)
    monkeypatch.setattr(native.u, "GetDlgCtrlID", lambda *a: cid)
    monkeypatch.setattr(native, "control_ids", lambda *a: frozenset(template["ids"]))
    monkeypatch.setattr(native, "is_main", lambda *a: False)
    monkeypatch.setattr(native.u, "PostMessageW", lambda *a: posted.append(a) or 1)
    return posted, confirmation


def test_power_command_is_not_sent_without_confirmation(app, monkeypatch):
    posted, confirmation = prepare(app, monkeypatch, "PowerManager.exe_5_16007_1033", 1)
    app.activate_control(55)
    assert len(confirmation) == 1
    assert posted == []


def test_changed_power_parameters_invalidate_confirmation(app, monkeypatch):
    posted, confirmation = prepare(app, monkeypatch, "PowerManager.exe_5_16007_1033", 1)
    app.activate_control(55)
    app.selection_summary = lambda root: "Другая команда"
    with pytest.raises(native.Unavailable, match="Параметры изменились"):
        confirmation[0][1]()
    assert posted == []


def test_confirmed_unchanged_command_dispatches_once(app, monkeypatch):
    posted, confirmation = prepare(app, monkeypatch, "PowerManager.exe_5_16007_1033", 1)
    app.activate_control(55)
    confirmation[0][1]()
    confirmation[0][1]()
    assert posted == [(55, 0xF5, 0, 0)]


def test_schedule_delete_without_selection_is_blocked(app, monkeypatch):
    posted, confirmation = prepare(app, monkeypatch, "PowerManager.exe_5_139_1033", 4)
    with pytest.raises(native.Unavailable, match="выберите запись"):
        app.activate_control(55)
    assert posted == confirmation == []


def test_enter_in_power_delay_field_uses_confirmation_gate(app, monkeypatch):
    posted, confirmation = prepare(app, monkeypatch, "PowerManager.exe_5_16007_1033", 1)
    sys.modules["api"].getFocusObject = lambda: SimpleNamespace(windowHandle=56, states=set())
    sys.modules["controlTypes"].State = SimpleNamespace(EXPANDED="expanded")
    monkeypatch.setattr(native, "class_name", lambda h: "Edit")
    app._root = lambda: 1000
    app._handle_error = lambda action: action()
    sent = []
    app.script_activate(SimpleNamespace(normalizedIdentifiers=["kb:enter"], send=lambda: sent.append(True)))
    assert len(confirmation) == 1
    assert posted == sent == []


def test_view_selection_waits_for_real_change_and_times_out(app):
    callbacks, dispatched, ready, failed = [], [], [], []
    sys.modules["core"].callLater = lambda delay, func, *args: callbacks.append(lambda: func(*args))
    app._view_generation = 0
    app._terminated = app._action_pending = False
    app.backend = SimpleNamespace(
        ensure_main_available=lambda: 100, current_view=lambda: "status", command=dispatched.append
    )
    app.select_view("table", lambda: ready.append(True), failed.append)
    while callbacks:
        callbacks.pop(0)()
    assert dispatched == ["table"] and ready == []
    assert len(failed) == 1 and "не переключила" in failed[0]


def test_newer_view_request_invalidates_previous_callback(app):
    callbacks, ready = [], []
    current = ["status"]
    sys.modules["core"].callLater = lambda delay, func, *args: callbacks.append(lambda: func(*args))
    app._view_generation = 0
    app._terminated = app._action_pending = False
    app.backend = SimpleNamespace(
        ensure_main_available=lambda: 100,
        current_view=lambda: current[0],
        command=lambda key: current.__setitem__(0, key),
    )
    app.select_view("table", lambda: ready.append("table"))
    app.select_view("curve", lambda: ready.append("curve"))
    while callbacks:
        callbacks.pop(0)()
    assert ready == ["curve"]


def test_reselecting_current_view_does_not_reset_graph(app):
    callbacks, dispatched, ready = [], [], []
    sys.modules["core"].callLater = lambda delay, func, *args: callbacks.append(lambda: func(*args))
    app._view_generation = 0
    app._terminated = app._action_pending = False
    app.backend = SimpleNamespace(
        ensure_main_available=lambda: 100, current_view=lambda: "curve", command=dispatched.append
    )
    app.select_view("curve", lambda: ready.append(True))
    callbacks.pop(0)()
    assert dispatched == [] and ready == [True]


@pytest.mark.parametrize("direction,focused,expected", [(1, 1012, 1014), (-1, 1012, 1013), (1, 1005, 1014)])
def test_original_header_navigation_only_moves_focus(app, monkeypatch, direction, focused, expected):
    moved = []
    app._root = lambda: 100
    app._handle_error = lambda action: action()
    app.focus_control = moved.append
    app.backend = SimpleNamespace(current_view=lambda: "status")
    monkeypatch.setattr(native, "is_main", lambda root: True)
    monkeypatch.setattr(native, "focused_control", lambda root: focused)
    monkeypatch.setattr(native.u, "GetDlgCtrlID", lambda hwnd: hwnd)
    monkeypatch.setattr(native.u, "GetDlgItem", lambda root, cid: cid)
    # No command/activate/show API is supplied: calling one must fail this test.
    app._switch_section(SimpleNamespace(send=lambda: pytest.fail("fallback")), direction)
    assert moved == [expected]


@pytest.mark.parametrize(
    "new_input,foreground,expected", [(False, 1000, [16025]), (True, 1000, []), (False, 2000, [])]
)
def test_radio_focus_retry_respects_new_input_or_other_window(
    app, monkeypatch, new_input, foreground, expected
):
    prepare(app, monkeypatch, "PowerManager.exe_5_16007_1033", 16014)
    callbacks, activated, moved = [], [], []
    app._root = lambda: 1000
    app._header_ids = lambda root: ()
    app._interaction_epoch, app._terminated = 0, False
    app._handle_error = lambda action: action()
    app.activate_control = activated.append
    app.focus_control = moved.append
    sys.modules["api"].getFocusObject = lambda: SimpleNamespace(
        windowControlID=16014, windowHandle=55, role="radio"
    )
    sys.modules["controlTypes"].Role = SimpleNamespace(RADIOBUTTON="radio")
    sys.modules["winUser"].getForegroundWindow = lambda: foreground
    sys.modules["core"].callLater = lambda delay, action, callback: callbacks.append(lambda: action(callback))
    monkeypatch.setattr(native.u, "GetDlgItem", lambda root, cid: cid)
    monkeypatch.setattr(native.u, "IsWindowVisible", lambda h: True)
    monkeypatch.setattr(native.u, "IsWindowEnabled", lambda h: True)
    app._switch_radio(SimpleNamespace(send=lambda: pytest.fail("fallback")), 1)
    assert activated == [16025]
    app._interaction_epoch += int(new_input)
    callbacks.pop()()
    assert moved == expected


@pytest.mark.parametrize("foreground,expected", [(100, True), (200, False)])
def test_focus_reconciliation_requires_real_windows_focus(app, monkeypatch, foreground, expected):
    callbacks, queued = [], []
    obj = SimpleNamespace(setFocus=lambda: None)
    # The fixture deliberately imports the entry without registering it in sys.modules.
    app.focus_control.__func__.__globals__["getNVDAObjectFromEvent"] = lambda *a: obj
    sys.modules["core"].callLater = lambda delay, func, *args: callbacks.append(lambda: func(*args))
    sys.modules["api"].getFocusObject = lambda: SimpleNamespace(windowHandle=999, processID=2)
    sys.modules["api"].setNavigatorObject = lambda obj: None
    sys.modules["winUser"].getForegroundWindow = lambda: foreground
    sys.modules["winUser"].setForegroundWindow = lambda root: None
    event_module = ModuleType("eventHandler")
    event_module.queueEvent = lambda *args: queued.append(args)
    monkeypatch.setitem(sys.modules, "eventHandler", event_module)
    monkeypatch.setattr(native.u, "GetAncestor", lambda *a: 100)
    monkeypatch.setattr(native.u, "GetParent", lambda *a: 0)
    monkeypatch.setattr(native, "focused_control", lambda root: 55)
    monkeypatch.setattr(native, "send", lambda *a: 1)
    app.backend = SimpleNamespace(validate_control=lambda h: None)
    app._focus_generation = 0
    app._terminated = False
    app.processID = 1
    app.focus_control(55)
    callbacks.pop(0)()
    assert bool(queued) is expected
    if expected:
        assert queued == [("gainFocus", obj)]
