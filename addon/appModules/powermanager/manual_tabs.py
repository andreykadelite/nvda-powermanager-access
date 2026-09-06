"""Native tabs with independent keyboard focus and explicit activation."""

import ui
import wx
import core
import api
import winUser

from . import native


def present_dialog(dialog, module, focus):
    """Retry a failed first foreground request, never refocus an active dialog."""
    epoch = module._interaction_epoch
    origin = winUser.getForegroundWindow()
    previous = api.getFocusObject()
    source = (
        native.u.GetAncestor(previous.windowHandle, 2) if previous.processID == module.processID else origin
    )

    def place():
        dialog.Show()
        winUser.setForegroundWindow(dialog.Handle)
        dialog.Raise()
        focus()

    place()

    def retry():
        if not dialog or module._terminated or epoch != module._interaction_epoch:
            return
        if dialog.IsActive() or winUser.getForegroundWindow() not in {origin, source}:
            return
        place()

    core.callLater(150, retry)


class ManualNotebook(wx.Notebook):
    def __init__(self, parent):
        super().__init__(parent)
        # TCS_BUTTONS is documented as dynamically changeable. With this style
        # TCM_SETCURFOCUS changes focus without selecting a page or notifying wx.
        style = native.u.GetWindowLongW(self.Handle, -16)
        native.u.SetWindowLongW(self.Handle, -16, style | 0x0100)
        if not native.u.GetWindowLongW(self.Handle, -16) & 0x0100:
            raise native.Unavailable("Не удалось включить ручное открытие вкладок.")

    @property
    def focused_index(self):
        index = native.send(self.Handle, 0x132F)  # TCM_GETCURFOCUS
        return index if 0 <= index < self.PageCount else max(0, self.Selection)

    def focus_header(self, index=None):
        if index is None:
            index = self.Selection
        self.SetFocus()
        native.send(self.Handle, 0x1330, index % self.PageCount)  # TCM_SETCURFOCUS
        handle, candidate = self.Handle, index % self.PageCount

        def reconcile():
            # wx briefly focuses the new page while committing. Its late MSAA
            # event can reach NVDA after the real focus has returned to a tab.
            # Never move Windows focus here or override a later user action.
            if not self or not native.u.IsWindow(handle):
                return
            root = native.u.GetAncestor(handle, 2)
            if winUser.getForegroundWindow() != root or native.focused_control(root) != handle:
                return
            if native.send(handle, 0x132F) != candidate:
                return
            focused = api.getFocusObject()
            if (
                focused.windowHandle == handle
                and getattr(focused, "IAccessibleChildID", None) == candidate + 1
            ):
                return
            from NVDAObjects.IAccessible import getNVDAObjectFromEvent
            import eventHandler

            obj = getNVDAObjectFromEvent(handle, -4, candidate + 1)
            if obj:
                eventHandler.queueEvent("gainFocus", obj)

        core.callLater(250, reconcile)

    def move_header(self, direction):
        index = self.focused_index if wx.Window.FindFocus() == self else self.Selection
        self.focus_header(index + direction)

    def activate_focused(self):
        index = self.focused_index
        if index == self.Selection:
            ui.message("Эта вкладка уже открыта. Tab — перейти к её содержимому.")
            return
        self.SetSelection(index)
        self.focus_header(index)
        ui.message(f"Открыта вкладка «{self.GetPageText(index)}». Tab — содержимое.")

    def handle_key(self, event):
        """Consume only tab navigation; preserve arrows/Space in page controls."""
        key = event.GetKeyCode()
        if event.AltDown():
            return False
        if event.ControlDown():
            if key in (wx.WXK_TAB, wx.WXK_PAGEUP, wx.WXK_PAGEDOWN):
                reverse = key == wx.WXK_PAGEUP or (key == wx.WXK_TAB and event.ShiftDown())
                self.move_header(-1 if reverse else 1)
                return True
            return False
        if wx.Window.FindFocus() != self:
            return False
        if key in (wx.WXK_LEFT, wx.WXK_UP, wx.WXK_RIGHT, wx.WXK_DOWN):
            self.move_header(-1 if key in (wx.WXK_LEFT, wx.WXK_UP) else 1)
        elif key in (wx.WXK_HOME, wx.WXK_END):
            self.focus_header(0 if key == wx.WXK_HOME else self.PageCount - 1)
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            self.activate_focused()
        else:
            return False
        return True
