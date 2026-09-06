"""Standard notebook for the vendor's otherwise silent bitmap presentations."""

import core
import gui
import ui
import wx

from . import native
from .manual_tabs import ManualNotebook, present_dialog
from .views import VIEWS, VIEW_KEYS, VIEW_BY_KEY, NAVIGATION, GRAPH_ITEMS, state_items, measurement_items


class ViewDialog(wx.Dialog):
    def __init__(self, parent, module, key):
        super().__init__(
            parent,
            title="PowerManagerII — состояние и измерения",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.module = module
        self.closed = False
        self.ticket = 0
        self.busy = False
        self.focus_content_on_ready = False
        self.book = ManualNotebook(self)
        self.lists = []
        self.captions = []
        self.refresh_buttons = []
        self.indices = [0] * len(VIEWS)
        for view in VIEWS:
            page = wx.Panel(self.book)
            box = wx.BoxSizer(wx.VERTICAL)
            caption = wx.StaticText(page, label=view.purpose + "\nF5 — обновить; стрелки — читать строки.")
            self.captions.append(caption)
            box.Add(caption, 0, wx.ALL | wx.EXPAND, 10)
            box.Add(
                wx.StaticText(page, label=f"&Содержимое открытой вкладки «{view.name}»:"),
                0,
                wx.LEFT | wx.RIGHT,
                10,
            )
            values = wx.ListBox(page, choices=["Чтение данных…"], style=wx.LB_HSCROLL)
            values.SetSelection(0)
            self.lists.append(values)
            box.Add(values, 1, wx.ALL | wx.EXPAND, 10)
            refresh = wx.Button(page, label="&Обновить данные (F5)")
            refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
            self.refresh_buttons.append(refresh)
            if view.key != "curve":
                box.Add(refresh, 0, wx.ALL, 10)
            else:
                refresh.Hide()
                numbers = wx.Button(page, label="Читать &текущие измерения")
                numbers.Bind(wx.EVT_BUTTON, self.on_numbers)
                box.Add(numbers, 0, wx.ALL, 10)
                history = wx.Button(page, label="Открыть &историю измерений: записи и фильтр")
                history.Bind(wx.EVT_BUTTON, self.on_history)
                box.Add(history, 0, wx.ALL, 10)
            page.SetSizer(box)
            self.book.AddPage(page, view.name)
        self.book.ChangeSelection(VIEW_KEYS.index(key))
        self.book.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.book, 1, wx.ALL | wx.EXPAND, 8)
        hint = wx.StaticText(
            self,
            label="Стрелки и Control+Tab — фокус на вкладке; Enter / пробел — открыть. Tab / F6 — содержимое открытой вкладки. F10 — меню. Escape — закрыть.",
        )
        hint.Wrap(780)
        layout.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        menu = wx.Button(self, label="&Меню программы (F10)")
        menu.Bind(wx.EVT_BUTTON, self.on_menu)
        buttons.Add(menu, 0, wx.ALL, 8)
        close = wx.Button(self, wx.ID_CANCEL, label="&Вернуться в программу")
        close.Bind(wx.EVT_BUTTON, self.on_close)
        buttons.Add(close, 0, wx.ALL, 8)
        layout.Add(buttons, 0, wx.ALIGN_RIGHT)
        self.SetSizer(layout)
        self.SetSize((860, 600))
        self.SetMinSize((640, 430))
        self.CentreOnScreen()
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        self.render(key)

    @property
    def key(self):
        return VIEW_KEYS[self.book.Selection]

    def present(self, content=False):
        if self.closed or self.module._terminated:
            return
        present_dialog(
            self, self.module, self.lists[self.book.Selection].SetFocus if content else self.book.focus_header
        )

    def choose(self, key):
        index = VIEW_KEYS.index(key)
        if self.book.Selection != index:
            self.book.SetSelection(index)

    def render(self, key, announce=False):
        if self.closed or key != self.key:
            return
        index = self.book.Selection
        values = self.lists[index]
        selected = self.indices[index]
        try:
            if self.module.backend.current_view() != key:
                raise native.Unavailable("Программа ещё не переключила экран. F5 — повторить.")
            if key == "curve":
                rows = list(GRAPH_ITEMS)
                caption = "График: назначение и способы чтения числовых данных."
            else:
                snapshot = self.module.backend.snapshot()
                if key == "status":
                    rows = state_items(snapshot)
                else:
                    table = native.u.GetDlgItem(self.module.backend.main(), 1034)
                    rows = measurement_items(self.module.read_table(table), snapshot.connected)
                caption = f"{VIEW_BY_KEY[key].purpose}\nПрочитано в {snapshot.captured_at}. F5 — обновить."
            values.Set(rows)
            values.SetSelection(min(selected, len(rows) - 1))
            self.captions[index].SetLabel(caption)
            self.SetTitle(f"PowerManagerII — {VIEW_BY_KEY[key].name}; вкладка {index + 1} из 3")
            if announce:
                ui.message("Данные обновлены. " + values.GetStringSelection())
        except Exception as error:
            values.Set(["Не удалось прочитать эту вкладку. F5 — повторить."])
            values.SetSelection(0)
            self.module._handle_error(lambda error=error: (_ for _ in ()).throw(error))
        finally:
            self.busy = False
            self.refresh_buttons[index].Enable()
            self.Layout()

    def on_page(self, event):
        event.Skip()
        self.load()

    def load(self, announce=False):
        if self.closed:
            return
        self.ticket += 1
        ticket, key = self.ticket, self.key
        focus_content, self.focus_content_on_ready = self.focus_content_on_ready, False
        epoch = self.module._interaction_epoch
        self.busy = True
        values = self.lists[self.book.Selection]
        self.indices[self.book.Selection] = max(0, values.Selection)
        values.Set(["Чтение данных…"])
        values.SetSelection(0)
        self.captions[self.book.Selection].SetLabel(VIEW_BY_KEY[key].purpose + "\nЧтение данных…")
        self.refresh_buttons[self.book.Selection].Disable()
        self.SetTitle(f"PowerManagerII — {VIEW_BY_KEY[key].name}; вкладка {self.book.Selection + 1} из 3")

        def ready():
            if not self.closed and self.ticket == ticket:
                self.render(key, announce)
                if focus_content and self.IsActive() and epoch == self.module._interaction_epoch:
                    self.lists[self.book.Selection].SetFocus()

        def failed(message):
            if not self.closed and self.ticket == ticket:
                self.busy = False
                values.Set([message, "F5 — повторить чтение после закрытия мешающего окна."])
                values.SetSelection(0)
                self.refresh_buttons[self.book.Selection].Enable()
                ui.message(message)

        self.module.select_view(key, ready, failed)

    def on_refresh(self, event):
        if self.busy:
            ui.message("Чтение вкладки ещё выполняется.")
            return
        if self.key == "curve":
            ui.message(
                "График не передаёт числовые точки. Для свежих значений выберите вкладку «Текущие измерения»."
            )
            return
        self.load(announce=True)

    def on_key(self, event):
        key = event.GetKeyCode()
        if self.book.handle_key(event):
            return
        elif key == wx.WXK_F6:
            if wx.Window.FindFocus() == self.book:
                self.lists[self.book.Selection].SetFocus()
            else:
                self.book.focus_header()
        elif key == wx.WXK_F5:
            self.on_refresh(event)
        elif key == wx.WXK_F10:
            self.on_menu(event)
        elif key == wx.WXK_F1:
            ui.browseableMessage(
                VIEW_BY_KEY[self.key].purpose + "\n" + NAVIGATION, title="Как читать вкладки PowerManagerII"
            )
        else:
            event.Skip()

    def on_history(self, event):
        epoch = self.module._interaction_epoch
        self.on_close(None, restore=False)
        core.callLater(
            300,
            self.module._handle_error,
            lambda: (
                self.module.open_command("history")
                if not self.module._terminated and epoch == self.module._interaction_epoch
                else None
            ),
        )

    def on_numbers(self, event):
        self.focus_content_on_ready = True
        self.book.SetSelection(VIEW_KEYS.index("table"))
        self.book.focus_header()

    def on_menu(self, event):
        epoch = self.module._interaction_epoch
        self.on_close(None, restore=False)
        core.callLater(
            250,
            self.module._handle_error,
            lambda: (
                self.module.show_menu()
                if not self.module._terminated and epoch == self.module._interaction_epoch
                else None
            ),
        )

    def on_close(self, event, restore=True):
        if self.closed:
            return
        key = self.key
        epoch = self.module._interaction_epoch
        self.closed = True
        self.ticket += 1
        self.module._view_generation += 1
        if self.module._views is self:
            self.module._views = None
        self.Destroy()
        if restore and not self.module._terminated:

            def focus():
                if self.module._terminated or epoch != self.module._interaction_epoch:
                    return
                root = self.module.backend.main()
                current = self.module.backend.current_view() or key
                gui.mainFrame.prePopup()
                try:
                    self.module.focus_control(native.u.GetDlgItem(root, VIEW_BY_KEY[current].control_id))
                finally:
                    gui.mainFrame.postPopup()

            core.callLater(150, self.module._handle_error, focus)
