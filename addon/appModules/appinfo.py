"""Richcomm's separate Saved Files viewer, recognized by its resource signature."""

import appModuleHandler
import api
import controlTypes
import ui
import winUser
from NVDAObjects.IAccessible import IAccessible
from scriptHandler import script
from appModules.powermanager import native

SIGNATURE = frozenset({1, 1000, 1001, 1004, 1005})
NAMES = {
    1: "Закрыть сохранённые файлы",
    1000: "Закрытые приложения",
    1001: "Сохранённые файлы выбранного приложения",
}


def recognized(hwnd):
    return native.class_name(hwnd) == "#32770" and SIGNATURE <= native.control_ids(hwnd)


class SavedControl(IAccessible):
    def _get_description(self):
        if recognized(self.windowHandle):
            return "Tab — списки и закрытие; F1 — помощь; Escape — закрыть."
        return super()._get_description()

    def _get_name(self):
        if recognized(self.windowHandle):
            return "PowerManagerII — сохранённые файлы"
        if recognized(native.u.GetParent(self.windowHandle)):
            return NAMES.get(self.windowControlID, super()._get_name())
        return super()._get_name()


class SavedEntry(IAccessible):
    """The empty native list emits a phantom child with role UNKNOWN."""

    def _get_name(self):
        original = super()._get_name()
        if original:
            return original
        label = NAMES.get(self.windowControlID, "Список")
        try:
            if native.send(self.windowHandle, 0x18B) == 0:  # LB_GETCOUNT
                return label + ": записей нет"
        except native.Unavailable:
            return label + ": чтение временно недоступно"
        return label + f": запись {self.IAccessibleChildID}, текст не передан программой"

    def _get_role(self):
        return controlTypes.Role.LISTITEM


class AppModule(appModuleHandler.AppModule):
    scriptCategory = "PowerManagerII"

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        if isinstance(obj, IAccessible):
            root = native.u.GetAncestor(obj.windowHandle, 2)
            if recognized(root):
                if getattr(obj, "IAccessibleChildID", 0) == 0:
                    clsList.insert(0, SavedControl)
                elif obj.windowClassName == "ListBox":
                    clsList.insert(0, SavedEntry)

    @script(description="Закрыть сохранённые файлы PowerManagerII", gesture="kb:escape")
    def script_close(self, gesture):
        root = native.u.GetAncestor(api.getFocusObject().windowHandle, 2)
        if recognized(root):
            native.u.PostMessageW(root, 0x10, 0, 0)
        else:
            gesture.send()

    @script(
        description="Закрыть окно сохранённых файлов", gestures=["kb:enter", "kb:numpadEnter", "kb:space"]
    )
    def script_activate(self, gesture):
        focus = api.getFocusObject()
        root = native.u.GetAncestor(focus.windowHandle, 2)
        if (
            recognized(root)
            and native.class_name(focus.windowHandle) == "Button"
            and focus.windowControlID == 1
        ):
            native.u.PostMessageW(root, 0x10, 0, 0)
        else:
            gesture.send()

    @script(description="Помощь по сохранённым файлам PowerManagerII", gesture="kb:f1")
    def script_help(self, gesture):
        root = native.u.GetAncestor(winUser.getForegroundWindow(), 2)
        if not recognized(root):
            gesture.send()
            return
        ui.browseableMessage(
            "Первый список содержит приложения, закрытые PowerManagerII при завершении работы. "
            "Второй список показывает связанные сохранённые файлы. Tab переключает списки и кнопку закрытия; "
            "стрелки перемещают по записям. Если сохранённых данных нет, списки пусты. Escape закрывает окно.",
            title="PowerManagerII — сохранённые файлы",
        )
