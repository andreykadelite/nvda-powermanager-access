"""Narrow Win32 adapter. No injection, hooks, device I/O or configuration-file edits."""

import ctypes as c
from ctypes import wintypes as w

from .model import COMMAND_BY_KEY, MAIN_SIGNATURE, METRICS, STATUS_IDS, Snapshot, table_controls
from .labels import match_template, ORDERS, RADIO_GROUPS, TAB_GROUPS
from .views import VIEW_BY_ID, VIEW_BY_KEY

u = c.WinDLL("user32", use_last_error=True)
CALLBACK = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)


class GUIThreadInfo(c.Structure):
    _fields_ = [
        ("cbSize", w.DWORD),
        ("flags", w.DWORD),
        ("hwndActive", w.HWND),
        ("hwndFocus", w.HWND),
        ("hwndCapture", w.HWND),
        ("hwndMenuOwner", w.HWND),
        ("hwndMoveSize", w.HWND),
        ("hwndCaret", w.HWND),
        ("rcCaret", w.RECT),
    ]


for name, args, result in (
    ("EnumWindows", [CALLBACK, w.LPARAM], w.BOOL),
    ("EnumChildWindows", [w.HWND, CALLBACK, w.LPARAM], w.BOOL),
    ("GetWindowTextW", [w.HWND, w.LPWSTR, c.c_int], c.c_int),
    ("GetClassNameW", [w.HWND, w.LPWSTR, c.c_int], c.c_int),
    ("GetWindowThreadProcessId", [w.HWND, c.POINTER(w.DWORD)], w.DWORD),
    ("GetGUIThreadInfo", [w.DWORD, c.POINTER(GUIThreadInfo)], w.BOOL),
    ("GetDlgCtrlID", [w.HWND], c.c_int),
    ("GetDlgItem", [w.HWND, c.c_int], w.HWND),
    ("GetParent", [w.HWND], w.HWND),
    ("GetAncestor", [w.HWND, w.UINT], w.HWND),
    ("GetWindow", [w.HWND, w.UINT], w.HWND),
    ("IsWindow", [w.HWND], w.BOOL),
    ("IsWindowVisible", [w.HWND], w.BOOL),
    ("IsWindowEnabled", [w.HWND], w.BOOL),
    ("GetWindowRect", [w.HWND, c.POINTER(w.RECT)], w.BOOL),
    ("GetWindowLongW", [w.HWND, c.c_int], w.LONG),
    ("SetWindowLongW", [w.HWND, c.c_int, w.LONG], w.LONG),
    ("PostMessageW", [w.HWND, w.UINT, w.WPARAM, w.LPARAM], w.BOOL),
    (
        "SendMessageTimeoutW",
        [w.HWND, w.UINT, w.WPARAM, w.LPARAM, w.UINT, w.UINT, c.POINTER(c.c_size_t)],
        w.LPARAM,
    ),
):
    fn = getattr(u, name)
    fn.argtypes, fn.restype = args, result


class Unavailable(RuntimeError):
    pass


def window_text(hwnd):
    buf = c.create_unicode_buffer(4096)
    u.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value.strip()


def class_name(hwnd):
    buf = c.create_unicode_buffer(256)
    u.GetClassNameW(hwnd, buf, len(buf))
    return buf.value


def process_id(hwnd):
    pid = w.DWORD()
    u.GetWindowThreadProcessId(hwnd, c.byref(pid))
    return pid.value


def focused_control(root):
    info = GUIThreadInfo()
    info.cbSize = c.sizeof(info)
    thread = u.GetWindowThreadProcessId(root, None)
    return info.hwndFocus if thread and u.GetGUIThreadInfo(thread, c.byref(info)) else None


def active_section(root, template):
    probes = {
        "PMConfig.dll_5_101_1033": ((3, 1005), (4, 1016), (5, 1060), (6, 1062)),
        "PMConfig.dll_5_136_1033": ((3, 1004), (4, 1079), (5, 1075), (6, 1027), (7, 1003)),
    }
    return next(
        (cid for cid, marker in probes.get(template, ()) if u.IsWindowVisible(u.GetDlgItem(root, marker))),
        None,
    )


def children(hwnd, direct=False):
    result = []

    @CALLBACK
    def collect(ch, _):
        if not direct or u.GetParent(ch) == hwnd:
            result.append(ch)
        return len(result) < 1024

    u.EnumChildWindows(hwnd, collect, 0)
    return result


def control_ids(hwnd):
    return frozenset(u.GetDlgCtrlID(ch) for ch in children(hwnd, direct=True))


def is_main(hwnd):
    return class_name(hwnd) == "#32770" and MAIN_SIGNATURE <= control_ids(hwnd)


def rect(hwnd):
    r = w.RECT()
    u.GetWindowRect(hwnd, c.byref(r))
    return r.left, r.top, r.right, r.bottom


def send(hwnd, message, wparam=0, lparam=0):
    result = c.c_size_t()
    if not u.SendMessageTimeoutW(hwnd, message, wparam, lparam, 0x22, 250, c.byref(result)):
        raise Unavailable("PowerManagerII не ответил. Повторите команду после закрытия занятых диалогов.")
    return result.value


class Backend:
    def __init__(self, pid, read_table=None):
        self.pid = pid
        self.read_table = read_table

    def windows(self):
        result = []

        @CALLBACK
        def collect(hwnd, _):
            if process_id(hwnd) == self.pid and class_name(hwnd) == "#32770":
                result.append(hwnd)
            return True

        u.EnumWindows(collect, 0)
        return result

    def main(self):
        found = [h for h in self.windows() if is_main(h)]
        if len(found) != 1:
            raise Unavailable("Откройте главное окно поддерживаемой версии PowerManagerII.")
        return found[0]

    def snapshot(self):
        root = self.main()
        # A cheap bounded response check distinguishes a hung UI from a live display.
        send(root, 0)
        table = u.GetDlgItem(root, 1034)
        if table and u.IsWindowVisible(table):
            if not self.read_table:
                raise Unavailable("Для чтения таблицы запустите дополнение внутри NVDA.")
            return Snapshot.from_controls(
                table_controls(self.read_table(table), window_text(u.GetDlgItem(root, 1029)))
            )
        if not u.IsWindowVisible(u.GetDlgItem(root, 1002)):
            raise Unavailable(
                "В режиме графика числовые индикаторы не обновляются. Откройте экран состояния: NVDA+Alt+F6."
            )
        ids = [cid for cid, _, _ in METRICS] + list(STATUS_IDS) + [1029]
        return Snapshot.from_controls({cid: window_text(u.GetDlgItem(root, cid)) for cid in ids})

    def current_view(self):
        root = self.main()
        if u.IsWindowVisible(u.GetDlgItem(root, 1034)):
            return "table"
        if u.IsWindowVisible(u.GetDlgItem(root, 1002)):
            return "status"
        if any(class_name(h) == "AfxOleControl42" and u.IsWindowVisible(h) for h in children(root)):
            return "curve"
        return None

    def command(self, key):
        command = COMMAND_BY_KEY[key]  # Deliberate allow-list; arbitrary IDs are not accepted.
        root = self.ensure_main_available()
        if not u.PostMessageW(root, 0x111, command.command_id, 0):
            raise Unavailable("Не удалось передать команду PowerManagerII.")

    def ensure_main_available(self):
        root = self.main()
        dialogs = [h for h in self.windows() if h != root and u.IsWindowVisible(h)]
        if dialogs or not u.IsWindowVisible(root) or not u.IsWindowEnabled(root):
            raise Unavailable("Сначала закройте открытый диалог PowerManagerII и вернитесь в главное окно.")
        send(root, 0)
        return root

    def validate_control(self, hwnd):
        if not u.IsWindow(hwnd) or process_id(hwnd) != self.pid:
            raise Unavailable("Элемент уже закрыт. Обновите список элементов.")
        if not u.IsWindowVisible(hwnd) or not u.IsWindowEnabled(hwnd):
            raise Unavailable("Элемент скрыт или недоступен.")
        root = u.GetAncestor(hwnd, 2)
        if not u.IsWindowEnabled(root):
            raise Unavailable("Это окно заблокировано открытым диалогом. Сначала закройте диалог.")
        send(root, 0)

    def visible_controls(self, root, include_disabled=False):
        if process_id(root) != self.pid:
            raise Unavailable("Это окно не принадлежит PowerManagerII.")
        allowed = {
            "Button",
            "Edit",
            "ComboBox",
            "SysListView32",
            "SysTabControl32",
            "SysDateTimePick32",
            "SysIPAddress32",
            "SysTreeView32",
            "ListBox",
        }
        result = [
            h
            for h in children(root)
            if class_name(h) in allowed
            and u.IsWindowVisible(h)
            and (include_disabled or u.IsWindowEnabled(h))
            and not (class_name(h) == "Button" and u.GetWindowLongW(h, -16) & 0xF == 7)
        ]
        # Composite controls implement their own arrow-key navigation.
        result = [
            h
            for h in result
            if class_name(u.GetParent(h)) not in {"ComboBox", "SysIPAddress32", "SysDateTimePick32"}
        ]
        if is_main(root):
            order = [
                1012,
                1014,
                1013,
                1005,
                1006,
                1007,
                1008,
                1009,
                1010,
                1011,
                1016,
                1017,
                1018,
                1019,
                1020,
                1022,
                1034,
                1001,
                1033,
                1032,
            ]
            current = self.current_view()
            if not include_disabled and current:
                selected = VIEW_BY_KEY[current].control_id
                result = [
                    h for h in result if u.GetDlgCtrlID(h) not in VIEW_BY_ID or u.GetDlgCtrlID(h) == selected
                ]
            return sorted(
                result,
                key=lambda h: order.index(u.GetDlgCtrlID(h)) if u.GetDlgCtrlID(h) in order else len(order),
            )
        template = match_template(control_ids(root))
        if template and not include_disabled:
            tabs = TAB_GROUPS.get(template["key"], ())
            selected_tab = active_section(root, template["key"])
            if tabs and selected_tab:
                result = [
                    h for h in result if u.GetDlgCtrlID(h) not in tabs or u.GetDlgCtrlID(h) == selected_tab
                ]
            # Focusing every radio in this vendor UI changes which fields are enabled.
            # Use standard dialog navigation: Tab visits the selected option, arrows choose another.
            for group in RADIO_GROUPS.get(template["key"], ()):
                choices = [h for h in result if u.GetDlgCtrlID(h) in group]
                selected = next((h for h in choices if send(h, 0xF0) == 1), choices[0] if choices else None)
                result = [h for h in result if h not in choices or h == selected]
        if template and template["key"] in ORDERS:
            order = ORDERS[template["key"]]
            return sorted(
                result,
                key=lambda h: order.index(u.GetDlgCtrlID(h)) if u.GetDlgCtrlID(h) in order else len(order),
            )
        return sorted(result, key=lambda h: (rect(h)[1] // 8, rect(h)[0]))

    def active_dialog(self):
        candidates = [h for h in self.windows() if u.IsWindowVisible(h) and u.IsWindowEnabled(h)]
        if not candidates:
            raise Unavailable("Нет доступного окна PowerManagerII.")
        return next((h for h in candidates if not is_main(h)), candidates[0])

    def selected_row(self, root, cid):
        hwnd = u.GetDlgItem(root, cid)
        if not hwnd or not u.IsWindowVisible(hwnd):
            return False
        return send(hwnd, 0x1032) > 0  # LVM_GETSELECTEDCOUNT; no cross-process pointers.
