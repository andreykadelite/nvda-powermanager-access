"""Accessible wxWidgets command panel hosted by NVDA."""

import core
import api
import ui
import wx
from NVDAObjects.IAccessible import getNVDAObjectFromEvent

from . import native
from .manual_tabs import ManualNotebook, present_dialog
from .model import COMMANDS
from .help import help_for
from .reports import history_page


class AccessPanel(wx.Dialog):
    def __init__(self, parent, module, source_root):
        super().__init__(
            parent,
            title="PowerManagerII — доступная панель",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.module = module
        self.source_root = source_root
        current_focus = api.getFocusObject()
        self.source_focus = (
            current_focus.windowHandle if current_focus.processID == module.processID else None
        )
        self.control_handles = []
        self._closed = False
        self.book = ManualNotebook(self)
        status = wx.Panel(self.book)
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(status, label="&Состояние ИБП (F5 — обновить):"), 0, wx.ALL, 8)
        self.report = wx.TextCtrl(status, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        box.Add(self.report, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        refresh = wx.Button(status, label="&Обновить показания")
        refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        box.Add(refresh, 0, wx.ALL, 8)
        self.watch = wx.CheckBox(status, label="Сообщать об изменении статусов (проверка раз в 5 секунд)")
        self.watch.SetValue(module._watch_enabled)
        self.watch.Bind(wx.EVT_CHECKBOX, self.on_watch)
        box.Add(self.watch, 0, wx.ALL, 8)
        status.SetSizer(box)
        self.book.AddPage(status, "Состояние")
        actions = wx.Panel(self.book)
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(actions, label="&Команды PowerManagerII:"), 0, wx.ALL, 8)
        self.commands = wx.ListBox(actions, choices=[c.label for c in COMMANDS])
        self.commands.SetSelection(0)
        box.Add(self.commands, 1, wx.EXPAND | wx.ALL, 8)
        run = wx.Button(actions, label="&Открыть или выполнить выбранную команду")
        run.Bind(wx.EVT_BUTTON, self.on_command)
        self.commands.Bind(wx.EVT_LISTBOX_DCLICK, self.on_command)
        box.Add(run, 0, wx.ALL, 8)
        actions.SetSizer(box)
        self.book.AddPage(actions, "Команды")
        controls = wx.Panel(self.book)
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(controls, label="&Элементы исходного окна:"), 0, wx.ALL, 8)
        self.controls = wx.ListBox(controls)
        box.Add(self.controls, 1, wx.EXPAND | wx.ALL, 8)
        focus = wx.Button(controls, label="&Перейти к выбранному элементу")
        focus.Bind(wx.EVT_BUTTON, self.on_focus)
        self.controls.Bind(wx.EVT_LISTBOX_DCLICK, self.on_focus)
        box.Add(focus, 0, wx.ALL, 8)
        text = wx.Button(controls, label="&Прочитать текст и таблицы исходного окна")
        text.Bind(wx.EVT_BUTTON, self.on_text)
        box.Add(text, 0, wx.ALL, 8)
        controls.SetSizer(box)
        self.book.AddPage(controls, "Элементы окна")
        help_page = wx.Panel(self.book)
        help_box = wx.BoxSizer(wx.VERTICAL)
        help_box.Add(wx.StaticText(help_page, label="Помощь по исходному окну:"), 0, wx.ALL, 8)
        help_text = wx.TextCtrl(
            help_page, value=help_for(native.control_ids(source_root)), style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        help_box.Add(help_text, 1, wx.EXPAND | wx.ALL, 8)
        help_page.SetSizer(help_box)
        self.book.AddPage(help_page, "Помощь")
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.book, 1, wx.EXPAND | wx.ALL, 8)
        layout.Add(
            wx.StaticText(
                self,
                label="Control+Tab и стрелки — фокус на вкладке; Enter / пробел — открыть; Tab — содержимое.",
            ),
            0,
            wx.ALL,
            8,
        )
        close = wx.Button(self, wx.ID_CANCEL, label="&Закрыть")
        close.Bind(wx.EVT_BUTTON, self.on_close)
        layout.Add(close, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(layout)
        self.SetSize((800, 580))
        self.SetMinSize((560, 400))
        self.CentreOnScreen()
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.on_refresh(None)
        self.load_controls()
        if self.book.Selection == 0:
            self.report.SetFocus()

    def present(self):
        present_dialog(self, self.module, self.report.SetFocus)

    def on_refresh(self, event):
        try:
            self.report.ChangeValue(self.module.backend.snapshot().report())
            self.report.SetInsertionPoint(0)
            if event:
                ui.message("Показания обновлены")
        except native.Unavailable as error:
            self.report.ChangeValue(str(error))
        except Exception:
            self.module._handle_error(lambda: self.module.backend.snapshot())
            self.report.ChangeValue("Чтение недоступно. F5 — повторить.")

    def on_key(self, event):
        if self.book.handle_key(event):
            return
        if event.GetKeyCode() == wx.WXK_F5:
            self.on_refresh(event)
            self.load_controls()
        elif event.GetKeyCode() == wx.WXK_F1:
            self.book.SetSelection(3)
            self.book.GetPage(3).GetChildren()[-1].SetFocus()
        elif event.GetKeyCode() == wx.WXK_RETURN and wx.Window.FindFocus() == self.commands:
            self.on_command(event)
        else:
            event.Skip()

    def on_watch(self, event):
        self.module.script_monitor(None)
        self.watch.SetValue(self.module._watch_enabled)

    def load_controls(self):
        self.controls.Clear()
        self.control_handles = []
        try:
            for hwnd in self.module.backend.visible_controls(self.source_root, include_disabled=True):
                obj = getNVDAObjectFromEvent(hwnd, -4, 0)
                name = (obj.name if obj else "") or native.window_text(hwnd)
                if not name:
                    name = f"Элемент {native.u.GetDlgCtrlID(hwnd)}"
                role = obj.role.displayString if obj else native.class_name(hwnd)
                state = (
                    " (недоступно; зависит от выбранных параметров)"
                    if not native.u.IsWindowEnabled(hwnd)
                    else ""
                )
                self.controls.Append(f"{name} — {role}{state}")
                self.control_handles.append(hwnd)
            if self.control_handles:
                self.controls.SetSelection(0)
        except native.Unavailable as error:
            self.controls.Append(str(error))

    def on_command(self, event):
        index = self.commands.GetSelection()
        if index == wx.NOT_FOUND:
            return
        command = COMMANDS[index]
        try:
            self.module.request_command(command.key)
        except native.Unavailable as error:
            ui.message(str(error))
            return
        except Exception as error:

            def fail(error=error):
                raise error

            self.module._handle_error(fail)
            return
        self.on_close(None, restore=False)

    def on_focus(self, event):
        index = self.controls.GetSelection()
        if not 0 <= index < len(self.control_handles):
            return
        hwnd = self.control_handles[index]
        try:
            self.module.backend.validate_control(hwnd)
        except native.Unavailable as error:
            ui.message(str(error))
            return
        self.on_close(None, restore=False)
        self.restore_focus(hwnd)

    def on_text(self, event):
        self.module._handle_error(
            lambda: ui.browseableMessage(
                self.module.window_report(self.source_root), title="PowerManagerII — текст окна"
            )
        )

    def on_close(self, event, restore=True):
        if self._closed:
            return
        self._closed = True
        if self.module._panel is self:
            self.module._panel = None
        self.Destroy()
        if restore and self.source_focus:
            self.restore_focus(self.source_focus)

    def restore_focus(self, hwnd):
        module, epoch = self.module, self.module._interaction_epoch
        core.callLater(
            150,
            module._handle_error,
            lambda: (
                module.focus_control(hwnd)
                if not module._terminated and epoch == module._interaction_epoch
                else None
            ),
        )


class TableReader(wx.Dialog):
    """Read 50 records per action; never block NVDA by walking an unbounded grid."""

    page_size = 50

    def __init__(self, parent, module, table, title, history=False):
        super().__init__(
            parent, title=title + " — текстовые записи", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.module, self.table, self.history = module, table, history
        self.offset, self.total, self.closed = 0, 0, False
        module._readers.add(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(
            wx.StaticText(
                self, label="Записи таблицы (Control+PageDown / PageUp — страницы, F5 — обновить):"
            ),
            0,
            wx.ALL,
            8,
        )
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        layout.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.previous = wx.Button(self, label="&Предыдущие 50 записей")
        self.following = wx.Button(self, label="&Следующие 50 записей")
        self.previous.Bind(wx.EVT_BUTTON, lambda evt: self.page(-1))
        self.following.Bind(wx.EVT_BUTTON, lambda evt: self.page(1))
        close = wx.Button(self, wx.ID_CANCEL, label="&Закрыть")
        close.Bind(wx.EVT_BUTTON, self.on_close)
        for button in (self.previous, self.following, close):
            buttons.Add(button, 0, wx.ALL, 8)
        layout.Add(buttons)
        self.SetSizer(layout)
        self.SetSize((850, 600))
        self.SetMinSize((540, 360))
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.refresh()

    def present(self):
        if not self.closed and not self.module._terminated:
            present_dialog(self, self.module, self.text.SetFocus)

    def refresh(self):
        def read():
            self.module.backend.validate_control(self.table)
            self.total = native.send(self.table, 0x1004)
            if not 0 <= self.total <= 10000000:
                raise native.Unavailable("Размер таблицы не распознан.")
            self.offset = min(self.offset, max(0, (self.total - 1) // self.page_size * self.page_size))
            obj = getNVDAObjectFromEvent(self.table, -4, 0)
            if not obj:
                raise native.Unavailable("Таблица недоступна.")
            rows = [
                obj.getChild(i) for i in range(self.offset, min(self.total, self.offset + self.page_size))
            ]
            text = (
                history_page([[c.name for c in row.children] for row in rows], self.offset, self.total)
                if self.history
                else "\n".join(row.name or "Пустая строка" for row in rows)
            )
            self.text.ChangeValue(text or "В списке нет записей.")
            self.text.SetInsertionPoint(0)
            self.previous.Enable(self.offset > 0)
            self.following.Enable(self.offset + self.page_size < self.total)

        try:
            read()
        except Exception as error:
            self.text.ChangeValue(str(error))
            self.previous.Disable()
            self.following.Disable()
            self.module._handle_error(lambda error=error: (_ for _ in ()).throw(error))

    def page(self, direction):
        proposed = self.offset + direction * self.page_size
        if proposed < 0 or proposed >= self.total:
            ui.message("Больше записей в этом направлении нет.")
            return
        self.offset = proposed
        self.refresh()
        self.text.SetFocus()
        ui.message(
            f"Записи {self.offset + 1}–{min(self.total, self.offset + self.page_size)} из {self.total}"
        )

    def on_key(self, event):
        if event.ControlDown() and event.GetKeyCode() in (wx.WXK_PAGEDOWN, wx.WXK_PAGEUP):
            self.page(1 if event.GetKeyCode() == wx.WXK_PAGEDOWN else -1)
        elif event.GetKeyCode() == wx.WXK_F5:
            self.refresh()
        else:
            event.Skip()

    def on_close(self, event):
        if self.closed:
            return
        self.closed = True
        self.module._readers.discard(self)
        self.Destroy()
        self.module._handle_error(lambda: self.module.focus_control(self.table))
