"""NVDA app module for the Richcomm PowerManagerII Windows client."""

import api
import appModuleHandler
import core
import controlTypes
import gui
import ui
import wx
import winUser
import time
import inputCore
from logHandler import log
from NVDAObjects.IAccessible import IAccessible, getNVDAObjectFromEvent
from scriptHandler import script

from . import native
from .labels import label_for, match_template, title_for, TAB_GROUPS, RADIO_GROUPS
from .model import ChangeTracker, MAIN_SIGNATURE, MENU_NAMES, MENU_GROUPS, COMMAND_BY_KEY
from .views import VIEW_BY_ID, VIEW_BY_KEY, VIEWS


class NamedControl(IAccessible):
    def _main_view(self):
        if self.windowControlID in VIEW_BY_ID and native.is_main(native.u.GetParent(self.windowHandle)):
            return VIEW_BY_ID[self.windowControlID]
        return None

    def _section(self):
        parent = native.u.GetParent(self.windowHandle)
        template = match_template(native.control_ids(parent))
        if template and self.windowControlID in TAB_GROUPS.get(template["key"], ()):
            return parent, template["key"]
        return None

    def _get_role(self):
        if self._main_view() or self._section():
            return controlTypes.Role.TAB
        return super()._get_role()

    def _get_states(self):
        states = super()._get_states()
        view = self._main_view()
        if view:
            states = states - {controlTypes.State.SELECTED}
            if self.appModule.backend.current_view() == view.key:
                states = states | {controlTypes.State.SELECTED}
            return states
        section = self._section()
        if section and native.active_section(*section) == self.windowControlID:
            states = states | {controlTypes.State.SELECTED}
        return states

    def _get_name(self):
        original = super()._get_name() or ""
        try:
            view = self._main_view()
            if view:
                return view.name
            parent = native.u.GetParent(self.windowHandle)
            template = match_template(native.control_ids(parent))
            if template and template["key"] == "PMConfig.dll_5_138_1033" and self.windowControlID == 1034:
                caption = native.window_text(native.u.GetDlgItem(parent, 1024)).rstrip(":").strip()
                return {
                    "Email Address": "Адрес электронной почты",
                    "Pager Number": "Номер пейджера",
                    "Mobile Phone Number": "Номер мобильного телефона",
                    "Telephone Number": "Номер телефона",
                }.get(caption, caption) or "Адрес или номер получателя"
            return label_for(native.control_ids(parent), self.windowControlID, self.windowClassName, original)
        except Exception:
            log.debugWarning("PowerManagerII: cannot name control", exc_info=True)
            return original

    def _get_description(self):
        view = self._main_view()
        if view:
            return f"{view.purpose} Стрелки и Control+Tab — фокус на вкладке; Enter или пробел — открыть; F6 — содержимое открытой вкладки."
        template = match_template(native.control_ids(native.u.GetParent(self.windowHandle)))
        if template and self.windowControlID in TAB_GROUPS.get(template["key"], ()):
            return "Раздел настроек. Стрелки и Control+Tab — фокус на разделе; Enter или пробел — открыть; Tab — параметры."
        return super()._get_description()

    def doAction(self, index=None):
        if self.windowClassName == "Button":
            return self.appModule._handle_error(lambda: self.appModule.activate_control(self.windowHandle))
        return super().doAction(index)


class NamedRow(IAccessible):
    def _get_name(self):
        original = super()._get_name() or ""
        parent = native.u.GetParent(self.windowHandle)
        name = label_for(native.control_ids(parent), self.windowControlID, "SysListView32", "Список")
        if not original.strip():
            return f"{name}: пустая строка"
        if native.is_main(parent) and self.windowControlID == 1001:
            return original.replace("Column 1:", "Событие:")
        return original


class NamedMenuItem(IAccessible):
    def _get_name(self):
        original = super()._get_name() or ""
        return MENU_NAMES.get(original.replace("&", "").strip(), original)


class NamedDialog(IAccessible):
    def _get_description(self):
        if native.is_main(self.windowHandle) or match_template(native.control_ids(self.windowHandle)):
            return ""
        return super()._get_description()

    def _get_name(self):
        if native.is_main(self.windowHandle):
            return "PowerManagerII"
        title = native.window_text(native.u.GetDlgItem(self.windowHandle, 1143))
        return title_for(
            native.control_ids(self.windowHandle), title or super()._get_name() or "PowerManagerII"
        )


class AppModule(appModuleHandler.AppModule):
    scriptCategory = "PowerManagerII"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = native.Backend(self.processID, read_table=self.read_table)
        self._panel = None
        self._views = None
        self._view_generation = 0
        self._observed_view = None
        self._readers = set()
        self._watch = None
        self._watch_enabled = False
        self._tracker = ChangeTracker()
        self._watch_error = False
        self._terminated = False
        self._action_pending = False
        self._confirmation = None
        self._focus_generation = 0
        self._last_focus = {}
        self._last_activation = (0, 0.0)
        self._pending_return = False
        self._switch_epoch = 0
        self._interaction_epoch = 0
        inputCore.decide_executeGesture.register(self._route_navigation)
        log.info("PowerManagerII Access: application module loaded")

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        if not isinstance(obj, IAccessible) or not getattr(obj, "windowHandle", 0):
            return
        cls = obj.windowClassName
        if obj.role == controlTypes.Role.MENUITEM:
            clsList.insert(0, NamedMenuItem)
            return
        if getattr(obj, "IAccessibleChildID", 0) != 0:
            if cls == "SysListView32" and obj.role == controlTypes.Role.LISTITEM:
                clsList.insert(0, NamedRow)
            return
        if cls == "#32770":
            clsList.insert(0, NamedDialog)
        elif cls in {
            "Button",
            "Edit",
            "Static",
            "ComboBox",
            "SysListView32",
            "SysDateTimePick32",
            "SysIPAddress32",
        }:
            clsList.insert(0, NamedControl)

    def _root(self):
        foreground = winUser.getForegroundWindow()
        if native.process_id(foreground) == self.processID:
            return native.u.GetAncestor(foreground, 2)
        focus = api.getFocusObject()
        if focus.processID != self.processID:
            raise native.Unavailable("Перейдите в окно PowerManagerII.")
        return native.u.GetAncestor(focus.windowHandle, 2)

    def event_appModule_gainFocus(self):
        self._pending_return = True
        try:
            self._observed_view = self.backend.current_view()
        except native.Unavailable:
            pass

    def event_show(self, obj, nextHandler):
        nextHandler()
        if not getattr(obj, "windowHandle", 0):
            return
        if not (obj.windowControlID in {1002, 1034} or obj.windowClassName == "AfxOleControl42"):
            return
        root = native.u.GetAncestor(obj.windowHandle, 2)
        if not native.is_main(root):
            return

        def notice():
            if self._terminated or self._views or winUser.getForegroundWindow() != root:
                return
            current = self.backend.current_view()
            if current and current != self._observed_view:
                self._observed_view = current
                ui.message(
                    f"Выбрана вкладка «{VIEW_BY_KEY[current].name}». F6 — открыть её содержимое. Control+Tab — следующая вкладка."
                )

        core.callLater(250, self._handle_error, notice)

    def _route_navigation(self, gesture):
        """TabReporter binds Tab globally. Keep NVDA's normal execution/input-help pipeline."""
        ids = set(gesture.normalizedIdentifiers)
        self._interaction_epoch += 1
        self._focus_generation += 1
        if any("tab" in i.split(":")[-1].split("+") and "alt" in i.split(":")[-1].split("+") for i in ids):
            self._switch_epoch += 1
        focus = api.getFocusObject()
        if self._terminated or self.sleepMode or not focus or focus.processID != self.processID:
            return True
        if not ids & {"kb:tab", "kb:shift+tab"}:
            return True
        binding = gesture.script
        owner = getattr(binding, "__self__", None)
        if not owner or not type(owner).__module__.startswith("globalPlugins.TabReporter"):
            return True
        replacement = (
            self.script_nextControl
            if "kb:tab" in ids
            else (self.script_previousControl if "kb:shift+tab" in ids else None)
        )
        if replacement:
            root = self._root()
            controls = native.control_ids(root)
            if native.is_main(root) or match_template(controls):
                gesture.script = replacement
        return True

    def event_gainFocus(self, obj, nextHandler):
        try:
            root = native.u.GetAncestor(obj.windowHandle, 2)
            if obj.role not in {controlTypes.Role.MENU, controlTypes.Role.MENUITEM}:
                if self._pending_return:
                    self._pending_return = False
                    hint = (
                        "Control+Tab — вкладки; F6 — содержимое; F10 — меню."
                        if native.is_main(root)
                        else "F1 — помощь по этому окну."
                    )
                    ui.message(f"{title_for(native.control_ids(root), 'PowerManagerII')}. {hint}")
                if obj.windowHandle in self.backend.visible_controls(root):
                    self._last_focus[root] = obj.windowHandle
        except Exception:
            log.debugWarning("PowerManagerII: focus context unavailable", exc_info=True)
        nextHandler()

    def _handle_error(self, action):
        try:
            return action()
        except native.Unavailable as error:
            ui.message(str(error))
        except Exception:
            log.exception("PowerManagerII Access: command failed")
            ui.message("Не удалось выполнить команду PowerManagerII. Подробности в журнале NVDA.")

    @script(description="Открыть доступную панель PowerManagerII", gesture="kb:NVDA+alt+f1")
    def script_panel(self, gesture):
        def show():
            from .dialogs import AccessPanel

            if self._panel:
                self._panel.Raise()
                return
            root = self._root()
            gui.mainFrame.prePopup()
            try:
                self._panel = AccessPanel(gui.mainFrame, self, root)
                self._panel.present()
            finally:
                gui.mainFrame.postPopup()

        self._handle_error(show)

    @script(description="Прочитать состояние ИБП", gesture="kb:NVDA+alt+f2")
    def script_status(self, gesture):
        self._handle_error(lambda: ui.message(self.backend.snapshot().report()))

    @script(description="Открыть текстовый отчёт о состоянии ИБП", gesture="kb:NVDA+alt+f3")
    def script_report(self, gesture):
        self._handle_error(
            lambda: ui.browseableMessage(
                self.backend.snapshot().report(), title="PowerManagerII — состояние ИБП"
            )
        )

    @script(
        description="Включить или выключить сообщения об изменении статусов ИБП", gesture="kb:NVDA+alt+f5"
    )
    def script_monitor(self, gesture):
        self._watch_enabled = not self._watch_enabled
        if self._watch_enabled:
            self._tracker = ChangeTracker()
            self._poll()
        elif self._watch:
            self._watch.Stop()
            self._watch = None
        ui.message(
            "Сообщения об изменении статусов включены"
            if self._watch_enabled
            else "Сообщения об изменении статусов выключены"
        )

    def _poll(self):
        if self._terminated or not self._watch_enabled:
            return
        try:
            changes = self._tracker.update(self.backend.snapshot())
            if self._watch_error:
                ui.message("Чтение PowerManagerII восстановлено")
            self._watch_error = False
            if changes:
                ui.message("PowerManagerII. " + ". ".join(changes))
        except Exception:
            if not self._watch_error:
                ui.message("PowerManagerII: чтение состояния недоступно")
            self._watch_error = True
        self._watch = core.callLater(5000, self._poll)

    def focus_control(self, hwnd):
        self.backend.validate_control(hwnd)
        obj = getNVDAObjectFromEvent(hwnd, -4, 0)
        if obj is None:
            raise native.Unavailable("Не удалось получить доступ к элементу.")
        root = native.u.GetAncestor(hwnd, 2)
        if winUser.getForegroundWindow() != root:
            winUser.setForegroundWindow(root)
        # accSelect silently fails on several owner-drawn buttons, especially on re-entry.
        # Ask the actual dialog manager to focus the HWND; this also maintains dialog keyboard state.
        native.send(root, 0x28, hwnd, 1)  # WM_NEXTDLGCTL, explicit HWND.
        if native.focused_control(root) != hwnd:
            obj.setFocus()
        api.setNavigatorObject(obj)
        self._focus_generation += 1
        generation = self._focus_generation

        def check():
            if self._terminated or generation != self._focus_generation:
                return
            focused = api.getFocusObject()
            # Closing a wx window can deliver its former owner's focus event late.
            # Reconcile NVDA only when Windows independently confirms the exact target.
            root = native.u.GetAncestor(hwnd, 2)
            if winUser.getForegroundWindow() == root and native.focused_control(root) == hwnd:
                if focused.windowHandle != hwnd and native.u.GetParent(focused.windowHandle) != hwnd:
                    import eventHandler

                    eventHandler.queueEvent("gainFocus", obj)
                return
            if focused.processID != self.processID:
                return  # The user switched applications while a callback was pending.
            if native.focused_control(native.u.GetAncestor(hwnd, 2)) != hwnd and native.u.GetAncestor(
                focused.windowHandle, 2
            ) == native.u.GetAncestor(hwnd, 2):
                ui.message("Не удалось переместить фокус. Нажмите NVDA+Alt+F1 и выберите элемент в панели.")

        core.callLater(150, check)

    def open_command(self, key, confirmed=False):
        if self._action_pending and not confirmed:
            raise native.Unavailable("Сначала завершите открытое подтверждение PowerManagerII.")
        if key in VIEW_BY_KEY:
            return self.show_views(key)
        self.backend.command(key)
        if key in {"help", "saved", "quit"}:
            return
        epoch = self._interaction_epoch

        def focus_result():
            if self._terminated or epoch != self._interaction_epoch:
                return
            try:
                root = self.backend.main()
                dialogs = [
                    h
                    for h in self.backend.windows()
                    if h != root and native.u.IsWindowVisible(h) and native.u.IsWindowEnabled(h)
                ]
                target = dialogs[0] if dialogs else root
                controls = self.backend.visible_controls(target)
                if controls:
                    if key not in {"help", "saved", "quit"}:
                        gui.mainFrame.prePopup()
                        try:
                            self.focus_control(controls[0])
                        finally:
                            gui.mainFrame.postPopup()
                if target == root and key in {"status", "table"}:
                    ui.message(self.backend.snapshot().report())
                elif target == root and key == "curve":
                    ui.message(
                        "График текущих измерений. NVDA+Alt+F7 — числовая таблица; NVDA+Alt+F8 — текстовая история измерений."
                    )
            except native.Unavailable as error:
                ui.message(str(error))

        core.callLater(300, focus_result)

    def select_view(self, key, ready, failed=None):
        """Wait for the actual visible presentation before claiming a switch succeeded."""
        if key not in VIEW_BY_KEY:
            raise native.Unavailable("Неизвестная вкладка PowerManagerII.")
        self._view_generation += 1
        generation = self._view_generation

        def fail(error):
            if failed:
                failed(str(error))
            else:
                self._handle_error(lambda: (_ for _ in ()).throw(error))

        try:
            if self._action_pending:
                raise native.Unavailable("Сначала завершите открытое подтверждение.")
            self.backend.ensure_main_available()
            if self.backend.current_view() != key:
                self.backend.command(key)
        except Exception as error:
            fail(error)
            return

        def settle(attempt=0):
            if self._terminated or generation != self._view_generation:
                return
            try:
                self.backend.ensure_main_available()
                if self.backend.current_view() == key:
                    ready()
                elif attempt < 4:
                    core.callLater(150, settle, attempt + 1)
                else:
                    raise native.Unavailable(
                        "Программа не переключила вкладку. Повторите действие после закрытия открытых диалогов."
                    )
            except Exception as error:
                fail(error)

        core.callLater(150, settle)

    def show_views(self, key, focus_content=False):
        if self._views:
            self._views.choose(key)
            self._views.present(focus_content)
            return
        epoch = self._interaction_epoch

        def show():
            if self._terminated or epoch != self._interaction_epoch:
                return
            from .view_dialog import ViewDialog

            gui.mainFrame.prePopup()
            try:
                self._views = ViewDialog(gui.mainFrame, self, key)
                dialog = self._views
                dialog.present(focus_content)
            finally:
                gui.mainFrame.postPopup()

        self.select_view(key, show)

    @script(description="Перейти к содержимому выбранной вкладки PowerManagerII", gesture="kb:f6")
    def script_viewContent(self, gesture):
        def show():
            if not native.is_main(self._root()):
                gesture.send()
                return
            self.show_views(self.backend.current_view() or "status", focus_content=True)

        self._handle_error(show)

    def request_command(self, key):
        command = COMMAND_BY_KEY[key]
        if command.confirm:
            self.confirm_action(command.confirm, lambda: self.open_command(key, confirmed=True))
        else:
            self.open_command(key)

    def confirm_action(self, message, action):
        if self._action_pending:
            raise native.Unavailable("Сначала завершите открытое подтверждение.")
        root = self.backend.active_dialog()
        source_focus = native.focused_control(root)
        self._action_pending = True

        def show():
            if self._terminated:
                self._action_pending = False
                return
            dialog = None
            try:
                gui.mainFrame.prePopup()
                dialog = wx.GenericMessageDialog(
                    gui.mainFrame,
                    message,
                    "Подтверждение PowerManagerII",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
                )
                self._confirmation = dialog
                answer = dialog.ShowModal()
            finally:
                if dialog:
                    dialog.Destroy()
                self._confirmation = None
                self._action_pending = False
                gui.mainFrame.postPopup()
            if self._terminated:
                return
            if answer == wx.ID_YES:
                self._handle_error(action)
            elif source_focus and native.u.IsWindow(source_focus):
                self._handle_error(lambda: self.focus_control(source_focus))

        wx.CallAfter(self._handle_error, show)

    def activate_control(self, hwnd):
        self.backend.validate_control(hwnd)
        root = native.u.GetAncestor(hwnd, 2)
        cid = native.u.GetDlgCtrlID(hwnd)
        template = match_template(native.control_ids(root))
        key = template["key"] if template else ""
        if native.is_main(root) and cid in MENU_GROUPS:
            return self.show_menu(cid)
        if native.is_main(root) and cid in VIEW_BY_ID:
            return self.show_views(VIEW_BY_ID[cid].key)
        if native.is_main(root) and cid == 1017:
            return self.request_command("clear")
        required = {
            ("PowerManager.exe_5_139_1033", 1071): 1018,
            ("PowerManager.exe_5_139_1033", 4): 1018,
            ("PMConfig.dll_5_146_1033", 1020): 1039,
            ("PMConfig.dll_5_146_1033", 1021): 1039,
            ("PMConfig.dll_5_136_1033", 1020): 1018,
        }
        if (key, cid) in required and not self.backend.selected_row(root, required[(key, cid)]):
            raise native.Unavailable("Сначала выберите запись в списке стрелками вверх или вниз.")
        risk = {
            ("PowerManager.exe_5_16006_1033", 1): "Отправить выбранную команду тестирования реальному ИБП?",
            (
                "PowerManager.exe_5_16007_1033",
                1,
            ): "Отправить выбранную команду питания реальному ИБП? Питание подключённых устройств может отключиться.",
            (
                "PowerManager.exe_5_139_1033",
                3,
            ): "Добавить задачу в действующее расписание ИБП? Она будет выполняться автоматически.",
            ("PowerManager.exe_5_139_1033", 1071): "Изменить выбранную задачу в действующем расписании ИБП?",
            ("PowerManager.exe_5_139_1033", 4): "Удалить выбранную задачу из расписания ИБП?",
            ("PMConfig.dll_5_146_1033", 1021): "Удалить выбранного получателя оповещений?",
            ("PowerManager.exe_5_143_1033", 1): "Удалить записи истории согласно выбранному режиму?",
            ("PMConfig.dll_5_143_1033", 1): "Удалить записи истории согласно выбранному режиму?",
        }.get((key, cid))

        def perform():
            self.backend.validate_control(hwnd)
            if native.u.GetAncestor(hwnd, 2) != root or native.u.GetDlgCtrlID(hwnd) != cid:
                raise native.Unavailable("Окно изменилось. Повторите действие в текущем окне.")
            previous, stamp = self._last_activation
            if previous == hwnd and time.monotonic() - stamp < 0.5:
                return
            self._last_activation = (hwnd, time.monotonic())
            if not native.u.PostMessageW(hwnd, 0xF5, 0, 0):
                raise native.Unavailable("Кнопка не отвечает.")

        if risk:
            reviewed = self.selection_summary(root)
            selected_list = required.get((key, cid))
            selected_index = (
                native.send(native.u.GetDlgItem(root, selected_list), 0x100C, -1, 2)
                if selected_list
                else None
            )

            def confirmed_perform():
                self.backend.validate_control(hwnd)
                if self.selection_summary(root) != reviewed:
                    raise native.Unavailable(
                        "Параметры изменились после открытия подтверждения. Проверьте их и повторите команду."
                    )
                if (
                    selected_list
                    and native.send(native.u.GetDlgItem(root, selected_list), 0x100C, -1, 2) != selected_index
                ):
                    raise native.Unavailable("Выбрана другая запись. Повторите команду для текущей записи.")
                perform()

            return self.confirm_action(risk + "\n" + reviewed, confirmed_perform)
        perform()
        tabs = TAB_GROUPS.get(key, ())
        if cid in tabs:
            core.callLater(150, self._handle_error, lambda: self.announce_section(root, cid))
        else:
            epoch = self._interaction_epoch

            def focus_child_dialog():
                if self._terminated or epoch != self._interaction_epoch:
                    return
                target = winUser.getForegroundWindow()
                if target == root or native.process_id(target) != self.processID:
                    return
                if not match_template(native.control_ids(target)):
                    return
                controls = self.backend.visible_controls(target)
                if controls:
                    self.focus_control(controls[0])

            core.callLater(200, self._handle_error, focus_child_dialog)

    def selection_summary(self, root):
        lines = []
        for hwnd in self.backend.visible_controls(root):
            cls = native.class_name(hwnd)
            if cls == "Button" and native.u.GetWindowLongW(hwnd, -16) & 0xF in (2, 3, 4, 5, 6, 9):
                if native.send(hwnd, 0xF0) != 1:
                    continue
            elif cls not in {"Edit", "ComboBox", "SysDateTimePick32"}:
                continue
            obj = getNVDAObjectFromEvent(hwnd, -4, 0)
            if obj and controlTypes.State.PROTECTED not in obj.states:
                lines.append(
                    f"{obj.name}: {obj.value or native.window_text(hwnd)}" if cls != "Button" else obj.name
                )
        return "\n".join(lines)

    def announce_section(self, root, cid):
        controls = self.backend.visible_controls(root)
        template = match_template(native.control_ids(root))
        tabs = TAB_GROUPS.get(template["key"], ()) if template else ()
        if not template or native.active_section(root, template["key"]) != cid:
            return  # A newer activation already replaced this pending announcement.
        if winUser.getForegroundWindow() != root:
            return
        name = label_for(
            native.control_ids(root), cid, "Button", native.window_text(native.u.GetDlgItem(root, cid))
        )
        ui.message(f"Раздел {name}. Tab — перейти к параметрам.")
        self._last_focus[root] = native.u.GetDlgItem(root, cid)
        if not controls or not tabs:
            return

    def show_menu(self, cid=None):
        if not native.is_main(self._root()):
            raise native.Unavailable("Меню доступно в главном окне. Escape — закрыть текущий диалог.")

        def show():
            menu = wx.Menu()
            chosen = []
            epoch = self._switch_epoch
            root = self.backend.main()
            origin = native.focused_control(root) or native.u.GetDlgItem(root, 1005)
            groups = {cid: MENU_GROUPS[cid]} if cid else MENU_GROUPS
            for _, (title, keys) in groups.items():
                target = menu if cid else wx.Menu()
                for key in keys:
                    item = target.Append(wx.ID_ANY, COMMAND_BY_KEY[key].label)
                    target.Bind(wx.EVT_MENU, lambda evt, key=key: chosen.append(key), id=item.Id)
                if not cid:
                    menu.AppendSubMenu(target, title)
            gui.mainFrame.prePopup()
            try:
                gui.mainFrame.PopupMenu(menu)
            finally:
                menu.Destroy()
                gui.mainFrame.postPopup()
            if not self._terminated and epoch == self._switch_epoch:
                gui.mainFrame.prePopup()
                try:
                    self._handle_error(lambda: self.focus_control(origin))
                finally:
                    gui.mainFrame.postPopup()
                if chosen:
                    self._handle_error(lambda: self.request_command(chosen[0]))

        wx.CallAfter(self._handle_error, show)

    @script(description="Открыть меню PowerManagerII", gestures=["kb:f10", "kb:applications"])
    def script_menu(self, gesture):
        self._handle_error(self.show_menu)

    @script(
        description="Переместить фокус на следующую вкладку PowerManagerII",
        gestures=["kb:control+tab", "kb:control+pageDown"],
    )
    def script_nextSection(self, gesture):
        self._switch_section(gesture, 1)

    @script(
        description="Переместить фокус на предыдущую вкладку PowerManagerII",
        gestures=["kb:control+shift+tab", "kb:control+pageUp"],
    )
    def script_previousSection(self, gesture):
        self._switch_section(gesture, -1)

    def _switch_section(self, gesture, direction):
        root = self._root()
        tabs = self._header_ids(root)
        if not tabs:
            gesture.send()
            return
        focused = native.u.GetDlgCtrlID(native.focused_control(root) or 0)
        if focused in tabs:
            current = focused
        elif native.is_main(root):
            current = VIEW_BY_KEY[self.backend.current_view() or "status"].control_id
        else:
            template = match_template(native.control_ids(root))
            current = native.active_section(root, template["key"]) or tabs[0]
        cid = tabs[(tabs.index(current) + direction) % len(tabs)]
        self._handle_error(lambda: self.focus_control(native.u.GetDlgItem(root, cid)))

    @staticmethod
    def _header_ids(root):
        if native.is_main(root):
            return tuple(view.control_id for view in VIEWS)
        template = match_template(native.control_ids(root))
        return TAB_GROUPS.get(template["key"], ()) if template else ()

    @script(description="Выбрать следующий вариант в группе", gestures=["kb:rightArrow", "kb:downArrow"])
    def script_nextRadio(self, gesture):
        self._switch_radio(gesture, 1)

    @script(description="Выбрать предыдущий вариант в группе", gestures=["kb:leftArrow", "kb:upArrow"])
    def script_previousRadio(self, gesture):
        self._switch_radio(gesture, -1)

    def _switch_radio(self, gesture, direction):
        focus = api.getFocusObject()
        if focus.windowControlID in self._header_ids(native.u.GetAncestor(focus.windowHandle, 2)):
            return self._switch_section(gesture, direction)
        if focus.role != controlTypes.Role.RADIOBUTTON:
            gesture.send()
            return
        root = self._root()
        template = match_template(native.control_ids(root))
        groups = RADIO_GROUPS.get(template["key"], ()) if template else ()
        group = next((g for g in groups if focus.windowControlID in g), None)
        if not group:
            gesture.send()
            return
        choices = [
            cid
            for cid in group
            if native.u.IsWindowVisible(native.u.GetDlgItem(root, cid))
            and native.u.IsWindowEnabled(native.u.GetDlgItem(root, cid))
        ]
        if not choices:
            return
        cid = choices[(choices.index(focus.windowControlID) + direction) % len(choices)]
        hwnd = native.u.GetDlgItem(root, cid)
        self._handle_error(lambda: self.activate_control(hwnd))
        epoch = self._interaction_epoch
        core.callLater(
            60,
            self._handle_error,
            lambda: (
                self.focus_control(hwnd)
                if not self._terminated
                and epoch == self._interaction_epoch
                and winUser.getForegroundWindow() == root
                else None
            ),
        )

    @script(description="Закрыть текущий диалог PowerManagerII без сохранения", gesture="kb:escape")
    def script_cancelDialog(self, gesture):
        if controlTypes.State.EXPANDED in api.getFocusObject().states:
            gesture.send()
            return
        root = self._root()
        if native.is_main(root) or not match_template(native.control_ids(root)):
            gesture.send()
            return
        native.u.PostMessageW(root, 0x10, 0, 0)

    @script(description="Открыть экран состояния ИБП", gesture="kb:NVDA+alt+f6")
    def script_statusView(self, gesture):
        self._handle_error(lambda: self.open_command("status"))

    @script(description="Открыть таблицу всех параметров ИБП", gesture="kb:NVDA+alt+f7")
    def script_tableView(self, gesture):
        self._handle_error(lambda: self.open_command("table"))

    @staticmethod
    def read_table(hwnd):
        obj = getNVDAObjectFromEvent(hwnd, -4, 0)
        if not obj:
            raise native.Unavailable("Таблица PowerManagerII недоступна.")
        return [[cell.name for cell in obj.getChild(i).children] for i in range(min(obj.childCount, 32))]

    @script(description="Перейти к следующему доступному элементу PowerManagerII", gesture="kb:tab")
    def script_nextControl(self, gesture):
        self._move(gesture, 1)

    @script(description="Перейти к предыдущему доступному элементу PowerManagerII", gesture="kb:shift+tab")
    def script_previousControl(self, gesture):
        self._move(gesture, -1)

    def _move(self, gesture, direction):
        try:
            if controlTypes.State.EXPANDED in api.getFocusObject().states:
                gesture.send()
                return
            root = self._root()
            ids = native.control_ids(root)
            if not (MAIN_SIGNATURE <= ids or match_template(ids)):
                gesture.send()
                return
            controls = self.backend.visible_controls(root)
            if not controls:
                gesture.send()
                return
            focus = native.focused_control(root) or api.getFocusObject().windowHandle
            headers = self._header_ids(root)
            if native.u.GetDlgCtrlID(focus) in headers:
                # All presentation headers occupy one Tab stop. An unselected
                # focused header must still leave the group without opening it.
                focus = next((h for h in controls if native.u.GetDlgCtrlID(h) in headers), focus)
            while focus not in controls and focus and focus != root:
                focus = native.u.GetParent(focus)
            index = controls.index(focus) if focus in controls else (-1 if direction > 0 else 0)
            self.focus_control(controls[(index + direction) % len(controls)])
        except Exception:
            log.debugWarning("PowerManagerII: native Tab fallback", exc_info=True)
            gesture.send()

    @script(
        description="Активировать кнопку PowerManagerII", gestures=["kb:enter", "kb:numpadEnter", "kb:space"]
    )
    def script_activate(self, gesture):
        focus = api.getFocusObject()
        hwnd = focus.windowHandle
        if native.class_name(hwnd) != "Button":
            root = self._root()
            template = match_template(native.control_ids(root))
            key = template["key"] if template else ""
            enter = any(
                i.endswith(":enter") or i.endswith(":numpadenter") for i in gesture.normalizedIdentifiers
            )
            if enter and controlTypes.State.EXPANDED not in focus.states:
                if key in {
                    "PowerManager.exe_5_16006_1033",
                    "PowerManager.exe_5_16007_1033",
                    "PowerManager.exe_5_143_1033",
                    "PMConfig.dll_5_143_1033",
                }:
                    self._handle_error(lambda: self.activate_control(native.u.GetDlgItem(root, 1)))
                    return
                if key == "PowerManager.exe_5_139_1033":
                    ui.message(
                        "Для записи задачи перейдите к кнопке Добавить или Изменить. Параметры ещё не сохранены."
                    )
                    return
            gesture.send()
            return
        root = native.u.GetAncestor(hwnd, 2)
        ids = native.control_ids(root)
        if not (MAIN_SIGNATURE <= ids or match_template(ids)):
            gesture.send()
            return

        def activate():
            self.activate_control(hwnd)

        self._handle_error(activate)

    @script(description="Прочитать справку по текущему окну PowerManagerII", gesture="kb:f1")
    def script_contextHelp(self, gesture):
        from .help import help_for

        self._handle_error(
            lambda: ui.browseableMessage(
                help_for(native.control_ids(self._root())), title="PowerManagerII — помощь по окну"
            )
        )

    @script(description="Открыть текстовую историю измерений и анализ графика", gesture="kb:NVDA+alt+f8")
    def script_historyText(self, gesture):
        def show():
            root = self._root()
            history = next(
                (
                    h
                    for h in self.backend.windows()
                    if (match_template(native.control_ids(h)) or {}).get("key")
                    == "PowerManager.exe_5_148_1033"
                    and native.u.IsWindowVisible(h)
                ),
                None,
            )
            if history:
                table = native.u.GetDlgItem(history, 1036)
                if not native.u.IsWindowVisible(table):
                    self.activate_control(native.u.GetDlgItem(history, 1039))
                    ui.message("Открыта таблица истории. Фильтр задаёт период для текстового анализа.")
                from .dialogs import TableReader

                epoch = self._interaction_epoch

                def present_reader():
                    if self._terminated or epoch != self._interaction_epoch:
                        return
                    gui.mainFrame.prePopup()
                    try:
                        reader = TableReader(gui.mainFrame, self, table, "История измерений", history=True)
                        reader.present()
                    finally:
                        gui.mainFrame.postPopup()

                core.callLater(250, self._handle_error, present_reader)
            elif native.is_main(root):
                self.open_command("history")
                ui.message(
                    "История измерений. NVDA+Alt+F8 — читать записи и диапазоны значений; фильтр выбирает период."
                )
            else:
                raise native.Unavailable(
                    "Сначала закройте этот диалог. Текстовая история доступна в главном окне и окне истории измерений."
                )

        self._handle_error(show)

    @script(description="Прочитать доступный текст текущего окна PowerManagerII", gesture="kb:NVDA+alt+f4")
    def script_windowText(self, gesture):
        self._handle_error(
            lambda: ui.browseableMessage(
                self.window_report(self._root()), title="PowerManagerII — текст окна"
            )
        )

    def window_report(self, root):
        lines = []
        template = match_template(native.control_ids(root))
        lines.append(title_for(native.control_ids(root), native.window_text(native.u.GetDlgItem(root, 1143))))
        for hwnd in native.children(root):
            if not native.u.IsWindowVisible(hwnd):
                continue
            cls = native.class_name(hwnd)
            if cls == "Static":
                value = native.window_text(hwnd)
                if value and not value.startswith("IDB_") and value not in lines:
                    lines.append(value)
            elif cls == "Edit" and template and template["key"] == "PowerManager.exe_5_133_1033":
                obj = getNVDAObjectFromEvent(hwnd, -4, 0)
                if obj:
                    lines.append(f"{obj.name}: {obj.value or native.window_text(hwnd)}")
            elif cls == "SysListView32":
                obj = getNVDAObjectFromEvent(hwnd, -4, 0)
                if obj:
                    lines.append(obj.name or "Таблица")
                    count = min(obj.childCount, 100)
                    for i in range(count):
                        row = obj.getChild(i)
                        if row and row.name:
                            lines.append(row.name)
                    if obj.childCount > count:
                        lines.append(
                            "Показаны первые 100 строк. Все записи доступны в таблице; историю можно читать по страницам: NVDA+Alt+F8."
                        )
        return "\n".join(lines) or "В этом окне нет доступного текста. Используйте список элементов панели."

    def terminate(self):
        self._terminated = True
        inputCore.decide_executeGesture.unregister(self._route_navigation)
        if self._watch:
            self._watch.Stop()
            self._watch = None
        if self._confirmation:
            self._confirmation.EndModal(wx.ID_NO)
        if self._views:
            self._views.closed = True
            wx.CallAfter(self._views.Destroy)
            self._views = None
        if self._panel:
            panel, self._panel = self._panel, None
            wx.CallAfter(panel.Destroy)
        for reader in tuple(self._readers):
            reader.closed = True
            wx.CallAfter(reader.Destroy)
        self._readers.clear()
        super().terminate()
