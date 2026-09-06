"""Pure data model and verified command map, independent of NVDA and Windows."""

from dataclasses import dataclass
from datetime import datetime
import re


@dataclass(frozen=True)
class Command:
    key: str
    label: str
    command_id: int
    confirm: str = ""


# Extracted from RT_MENU 131 in the installed Richcomm executable.
COMMANDS = (
    Command("settings", "Настройки системы", 32776),
    Command("warnings", "Параметры оповещений", 32797),
    Command("recipients", "Получатели оповещений", 32790),
    Command("events", "История событий", 32781),
    Command("history", "История измерений", 32783),
    Command("status", "Вкладка: состояние ИБП", 32774),
    Command("curve", "Вкладка: график измерений", 32772),
    Command("table", "Вкладка: текущие измерения", 32773),
    Command("rating", "Номинальные параметры ИБП", 32775),
    Command("test", "Настройка самотестирования ИБП", 32786),
    Command("power", "Диалог выключения и включения ИБП", 32787),
    Command("schedule", "Расписание задач ИБП", 32788),
    Command("beeper", "Переключить звуковой сигнал ИБП", 32789, "Переключить звуковой сигнал самого ИБП?"),
    Command("saved", "Сохранённые файлы", 32791),
    Command(
        "clear",
        "Очистить поле событий главного окна",
        32778,
        "Очистить сообщения в поле событий главного окна?",
    ),
    Command("help", "Справка PowerManagerII", 32794),
    Command("about", "О PowerManagerII", 32793),
    Command("quit", "Закрыть клиент PowerManagerII", 32779),
)
COMMAND_BY_KEY = {c.key: c for c in COMMANDS}
MAIN_BUTTONS = {
    1005: "Система",
    1006: "Вид",
    1007: "Управление ИБП",
    1008: "Помощь",
    1009: "Настройки системы",
    1010: "История измерений",
    1011: "История событий",
    1012: "Состояние ИБП",
    1013: "График измерений",
    1014: "Текущие измерения",
    1016: "Номинальные параметры ИБП",
    1017: "Очистить поле событий",
    1018: "Расписание задач ИБП (Блок-схема ИБП)",
    1019: "Параметры оповещений",
    1020: "Получатели оповещений",
    1022: "Справка",
    1032: "Закрыть окно PowerManagerII",
    1033: "Свернуть окно",
}
MENU_GROUPS = {
    1005: ("Система", ("settings", "warnings", "recipients", "saved", "quit")),
    1006: ("Вид", ("status", "table", "curve", "events", "history", "rating", "clear")),
    1007: ("Управление ИБП", ("test", "power", "beeper", "schedule")),
    1008: ("Помощь", ("help", "about")),
}
# Match the actual translated native menu, including its misleading schedule label.
MENU_NAMES = {
    "Блок схема...": "Расписание задач ИБП (Блок-схема ИБП)",
    "Включить/Выключить": "Выключение и включение ИБП",
    "Тестирование...": "Самотестирование ИБП",
    "Блок-схема ИБП": "Расписание задач ИБП (Блок-схема ИБП)",
    "Просмотр вкладки данные": "Номинальные параметры ИБП",
    "Просмотр состояния диаграмм": "Вкладка: состояние ИБП",
    "Просмотр графика": "Вкладка: график измерений",
    "Просмотр списка действующих параметров ИБП": "Вкладка: текущие измерения",
    "Просмотр истории записи": "История измерений",
}
METRICS = (
    (1002, "Входное напряжение", "В"),
    (1038, "Входная частота", "Гц"),
    (1037, "Выходное напряжение", "В"),
    (1039, "Нагрузка", "%"),
    (1042, "Заряд батареи", "%"),
)
STATUS_IDS = (1023, 1024, 1025, 1026, 1027, 1028)
MAIN_SIGNATURE = frozenset((1002, 1023, 1029, 1037, 1038, 1039, 1042))
TABLE_IDS = {
    "входное напряжение": 1002,
    "input voltage": 1002,
    "выходное напряжение": 1037,
    "output voltage": 1037,
    "входная частота": 1038,
    "frequency": 1038,
    "input frequency": 1038,
    "нагрузка на ибп": 1039,
    "output load": 1039,
    "заряд батарей": 1042,
    "battery capability": 1042,
    "состояние сети": 1024,
    "ac indication": 1024,
    "напряжение батарей": 1025,
    "battery volt indication": 1025,
    "индикация байпас": 1028,
    "bypass indication": 1028,
    "сбой ибп": 1026,
    "ups failure indication": 1026,
    "режим тестирования": 1027,
    "test status": 1027,
    "индикатор подключение ибп": 1023,
    "ups connect indication": 1023,
}


def table_controls(rows, title):
    controls = {1029: title}
    for row in rows:
        for offset in (0, 3):
            if len(row) < offset + 2:
                continue
            key = (row[offset] or "").strip().casefold()
            if key in TABLE_IDS:
                controls[TABLE_IDS[key]] = row[offset + 1] or ""
    return controls


def numeric_value(text, unit):
    text = text.strip().rstrip("%").strip()
    if not re.fullmatch(r"-?\d+(?:[.,]\d+)?", text):
        return "нет данных"
    return f"{text.replace('.', ',')} {unit}"


@dataclass(frozen=True)
class Snapshot:
    title: str
    statuses: tuple[str, ...]
    metrics: tuple[tuple[str, str], ...]
    captured_at: str
    connected: bool | None

    @classmethod
    def from_controls(cls, controls, now=None):
        statuses = tuple(controls.get(cid, "").strip() for cid in STATUS_IDS)
        state = statuses[0].casefold()
        if any(s in state for s in ("disconnect", "отключ", "отсоедин", "нет связи")):
            connected = False
        elif any(s in state for s in ("connected", "подключ")):
            connected = True
        else:
            connected = None
        metrics = tuple(
            (
                label,
                numeric_value(controls.get(cid, ""), unit)
                if connected is True
                else "нет подтверждённых данных",
            )
            for cid, label, unit in METRICS
        )
        return cls(
            controls.get(1029, "PowerManagerII"),
            statuses,
            metrics,
            (now or datetime.now()).strftime("%H:%M:%S"),
            connected,
        )

    def report(self):
        lines = [self.title, f"Прочитано из PowerManagerII в {self.captured_at}"]
        lines += [s for s in self.statuses if s]
        if self.connected is not True:
            lines.append("Связь с ИБП не подтверждена. Числовые показания недоступны.")
        lines += [f"{name}: {value}" for name, value in self.metrics]
        return "\n".join(lines)


class ChangeTracker:
    """Announce status transitions once; never announce continuously varying voltages."""

    def __init__(self):
        self.previous = None

    def update(self, snapshot):
        current = snapshot.statuses
        previous, self.previous = self.previous, current
        if previous is None:
            return ()
        return tuple(new for old, new in zip(previous, current) if new and old != new)
