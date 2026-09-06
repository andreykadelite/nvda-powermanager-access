"""Keyboard intent must not select a page until explicit activation."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace, ModuleType
import sys

import pytest
from powermanager import native


@pytest.fixture
def notebook(monkeypatch):
    wx = ModuleType("wx")
    wx.Notebook = object
    keys = "TAB PAGEUP PAGEDOWN LEFT UP RIGHT DOWN HOME END RETURN NUMPAD_ENTER SPACE".split()
    for value, key in enumerate(keys, 1):
        setattr(wx, "WXK_" + key, value)
    ui = ModuleType("ui")
    ui.message = lambda message: None
    monkeypatch.setitem(sys.modules, "wx", wx)
    monkeypatch.setitem(sys.modules, "ui", ui)
    for name in ("api", "winUser", "core"):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    callbacks = []
    sys.modules["core"].callLater = lambda delay, callback: callbacks.append(callback)
    path = Path(__file__).resolve().parents[1] / "addon/appModules/powermanager/manual_tabs.py"
    spec = importlib.util.spec_from_file_location("powermanager.manual_tabs_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    book = object.__new__(module.ManualNotebook)
    book.Handle, book.PageCount, book.Selection = 42, 3, 0
    book.focus = 0
    book.commits = []
    book.callbacks = callbacks
    book.focus_owner = book
    wx.Window = SimpleNamespace(FindFocus=lambda: book.focus_owner)
    book.SetFocus = lambda: setattr(book, "focus_owner", book)
    book.GetPageText = lambda i: str(i)

    def select(index):
        book.commits.append(index)
        book.Selection = index

    def send(handle, message, index=0):
        assert handle == 42
        if message == 0x132F:
            return book.focus
        assert message == 0x1330
        book.focus = index

    book.SetSelection = select
    monkeypatch.setattr(native, "send", send)

    def key(name, control=False, shift=False, alt=False):
        return book.handle_key(
            SimpleNamespace(
                GetKeyCode=lambda: getattr(wx, "WXK_" + name),
                ControlDown=lambda: control,
                ShiftDown=lambda: shift,
                AltDown=lambda: alt,
            )
        )

    return book, key


@pytest.mark.parametrize(
    "name,control,shift,expected",
    [
        ("RIGHT", False, False, 1),
        ("LEFT", False, False, 2),
        ("DOWN", False, False, 1),
        ("UP", False, False, 2),
        ("TAB", True, False, 1),
        ("TAB", True, True, 2),
        ("PAGEDOWN", True, False, 1),
        ("PAGEUP", True, False, 2),
        ("HOME", False, False, 0),
        ("END", False, False, 2),
    ],
)
def test_navigation_moves_focus_without_selection(notebook, name, control, shift, expected):
    book, key = notebook
    assert key(name, control, shift)
    assert book.focus == expected and book.Selection == 0 and book.commits == []


@pytest.mark.parametrize("activation", ["RETURN", "NUMPAD_ENTER", "SPACE"])
def test_only_explicit_activation_selects_and_repeat_does_not_reload(notebook, activation):
    book, key = notebook
    key("RIGHT")
    key(activation)
    key(activation)
    assert book.Selection == 1 and book.commits == [1]


@pytest.mark.parametrize("name", ["UP", "DOWN", "SPACE", "RETURN", "HOME", "END", "TAB"])
def test_page_controls_keep_their_native_keys(notebook, name):
    book, key = notebook
    book.focus_owner = object()
    assert key(name) is False
    assert book.commits == []


def test_leaving_candidate_does_not_activate_and_ctrl_tab_starts_from_open_page(notebook):
    book, key = notebook
    key("END")
    assert key("TAB") is False
    book.focus_owner = object()
    key("TAB", control=True)
    assert book.focus == 1 and book.Selection == 0


@pytest.mark.parametrize(
    "native_focus,foreground,expected", [(42, 100, True), (43, 100, False), (42, 200, False)]
)
def test_accessibility_reconciliation_requires_exact_live_focus(
    notebook, monkeypatch, native_focus, foreground, expected
):
    book, key = notebook
    queued = []
    monkeypatch.setattr(native.u, "IsWindow", lambda h: True)
    monkeypatch.setattr(native.u, "GetAncestor", lambda *a: 100)
    monkeypatch.setattr(native, "focused_control", lambda h: native_focus)
    sys.modules["winUser"].getForegroundWindow = lambda: foreground
    sys.modules["api"].getFocusObject = lambda: SimpleNamespace(windowHandle=43)
    accessible = ModuleType("NVDAObjects.IAccessible")
    accessible.getNVDAObjectFromEvent = lambda *args: args
    monkeypatch.setitem(sys.modules, "NVDAObjects.IAccessible", accessible)
    handler = ModuleType("eventHandler")
    handler.queueEvent = lambda *args: queued.append(args)
    monkeypatch.setitem(sys.modules, "eventHandler", handler)
    key("RIGHT")
    book.callbacks.pop()()
    assert bool(queued) is expected
    if expected:
        assert queued == [("gainFocus", (42, -4, 2))]


@pytest.mark.parametrize(
    "active,later_epoch,foreground,retry",
    [(True, 0, 100, False), (False, 1, 100, False), (False, 0, 200, False), (False, 0, 100, True)],
)
def test_foreground_retry_never_resets_an_active_dialog_or_later_navigation(
    notebook, monkeypatch, active, later_epoch, foreground, retry
):
    book, key = notebook
    present = book.focus_header.__globals__["present_dialog"]
    placed, focused = [], []
    current = [100]
    sys.modules["winUser"].getForegroundWindow = lambda: current[0]
    sys.modules["winUser"].setForegroundWindow = lambda handle: None
    sys.modules["api"].getFocusObject = lambda: SimpleNamespace(windowHandle=55, processID=1)
    monkeypatch.setattr(native.u, "GetAncestor", lambda *a: 100)
    dialog = SimpleNamespace(
        Handle=500, Show=lambda: placed.append(True), Raise=lambda: None, IsActive=lambda: active
    )
    module = SimpleNamespace(_interaction_epoch=0, _terminated=False, processID=1)
    present(dialog, module, lambda: focused.append(True))
    module._interaction_epoch = later_epoch
    current[0] = foreground
    book.callbacks.pop()()
    assert len(placed) == len(focused) == 1 + int(retry)
