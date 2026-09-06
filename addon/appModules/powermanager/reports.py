"""Bounded, explicit text equivalent of measurement tables."""

from decimal import Decimal, InvalidOperation

HISTORY_COLUMNS = (
    "Дата и время",
    "Подключение",
    "Входное напряжение, В",
    "Входная частота, Гц",
    "Выходное напряжение, В",
    "Нагрузка, %",
    "Заряд батареи, %",
    "Температура, °C",
    "Напряжение батареи, В",
    "Состояние сети, код",
    "Состояние батареи, код",
    "Байпас, код",
    "Неисправность ИБП, код",
    "Тип ИБП, код",
    "Тестирование, код",
    "Выключение, код",
    "Звуковой сигнал, код",
    "Подключение ИБП, код",
)


def history_page(rows, offset, total):
    if not rows:
        return "В выбранном диапазоне нет записей."
    lines = [
        f"Записи {offset + 1}–{offset + len(rows)} из {total}.",
        "Исторические данные, загруженные PowerManagerII. Это не текущие показания.",
        "Минимум и максимум относятся только к показанным записям этой страницы.",
    ]
    for index in range(2, 9):
        values = []
        for row in rows:
            try:
                value = Decimal(str(row[index] or "").replace(",", "."))
                if value.is_finite():
                    values.append(value)
            except (InvalidOperation, IndexError):
                continue
        if values:
            lines.append(
                f"{HISTORY_COLUMNS[index]}: минимум {min(values)}, максимум {max(values)}".replace(".", ",")
            )
    for number, row in enumerate(rows, offset + 1):
        lines.append(f"\nЗапись {number}")
        lines.extend(f"{label}: {value or 'нет данных'}" for label, value in zip(HISTORY_COLUMNS, row))
    return "\n".join(lines)
