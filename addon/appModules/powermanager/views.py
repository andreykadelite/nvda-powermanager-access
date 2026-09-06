"""The three main presentations and their readable, source-labelled contents."""

from dataclasses import dataclass
from .model import numeric_value


@dataclass(frozen=True)
class View:
    key: str
    control_id: int
    name: str
    purpose: str


VIEWS = (
    View("status", 1012, "Состояние ИБП", "Связь, питание от сети, батарея и неисправности."),
    View(
        "table",
        1014,
        "Текущие измерения",
        "Напряжение, частота, заряд, нагрузка, температура и остальные параметры.",
    ),
    View("curve", 1013, "График измерений", "Изменение напряжений, заряда и нагрузки во времени."),
)
VIEW_BY_KEY = {v.key: v for v in VIEWS}
VIEW_BY_ID = {v.control_id: v for v in VIEWS}
VIEW_KEYS = tuple(v.key for v in VIEWS)
NAVIGATION = "Control+Tab и Control+Shift+Tab перемещают фокус между заголовками вкладок; на заголовках также работают стрелки, Home и End. Enter или пробел открывает вкладку в фокусе. Пока вы её не открыли, показаны прежние данные. Tab или F6 — содержимое открытой вкладки. В списке стрелки читают строки. F5 — обновить; повторное открытие той же вкладки не обновляет её. Escape — вернуться в программу. F10 — меню программы."


def state_items(snapshot):
    labels = (
        "Связь с ИБП",
        "Питание от сети",
        "Состояние батареи",
        "Неисправность ИБП",
        "Самотестирование",
        "Режим работы",
    )
    result = []
    for label, value in zip(labels, snapshot.statuses):
        if label == "Самотестирование" and value.strip() == "Отмена самотеста":
            value = "не выполняется"
        result.append(f"{label}: {value or 'нет данных'}")
    if snapshot.connected is not True:
        result.append("Связь не подтверждена. Числовые показания недоступны.")
    result.extend(
        f"{name}: {value}" for name, value in snapshot.metrics if name in {"Заряд батареи", "Нагрузка"}
    )
    return result


def measurement_items(rows, connected):
    """Flatten the vendor's two sets of three columns without losing signals."""
    labels = {
        "Заряд батарей": "Заряд батареи",
        "Нагрузка на ИБП": "Нагрузка",
        "Напряжение батарей": "Состояние батареи",
        "Индикация байпас": "Режим работы",
        "Сбой ИБП": "Неисправность ИБП",
        "ИБП типа": "Тип ИБП",
        "Индикатор выключение": "Выключение ИБП",
        "Индикатор подключение ИБП": "Связь с ИБП",
    }
    result = []
    for row in rows:
        for offset in (0, 3):
            if len(row) < offset + 2 or not row[offset]:
                continue
            original, value = row[offset].strip(), (row[offset + 1] or "").strip()
            if original in {"Наименование сигнала", "Signal Name"}:
                continue  # MSAA supplies the column header for the vendor's blank padding cells.
            unit = (row[offset + 2] or "").strip() if len(row) > offset + 2 else ""
            name = labels.get(original, original)
            if original == "Напряжение батарей" and unit:
                name = "Напряжение батареи"
            if unit:
                value = numeric_value(value, unit) if connected is True else "нет подтверждённых данных"
            elif value == "Отмена самотеста":
                value = "не выполняется"
            result.append(f"{name}: {value or 'нет данных'}")
    return result or ["Программа не передала строки измерений. F5 — повторить чтение."]


GRAPH_ITEMS = (
    "График открыт в главном окне PowerManagerII.",
    "Ось по горизонтали: время. Линии: входное и выходное напряжение, заряд батареи и нагрузка.",
    "Графический компонент не передаёт NVDA числовые точки кривых.",
    "Кнопка «Читать текущие измерения» переключит на вкладку с доступными числовыми значениями.",
    "Кнопка «Открыть историю измерений» открывает сохранённые записи с датами и фильтром периода.",
    "История записывается с интервалом из настроек программы; это отдельные сохранённые данные, а не все точки текущего графика.",
)
