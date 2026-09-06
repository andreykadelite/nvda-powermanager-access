from powermanager.reports import history_page


def test_history_explicitly_distinguishes_page_statistics_from_live_data():
    rows = [
        ["2026-09-06", "Auto", "0", "50", "230", "8", "94", "20.8", "26"],
        ["2026-09-05", "Auto", "230", "49", "231", "10", "80", "21", "27"],
    ]
    report = history_page(rows, 50, 123)
    assert "51–52 из 123" in report
    assert "не текущие показания" in report
    assert "Входное напряжение, В: минимум 0, максимум 230" in report
    assert "Запись 52" in report


def test_empty_history_has_no_invented_measurements():
    report = history_page([], 0, 0)
    assert "нет записей" in report
    assert "минимум" not in report


def test_invalid_and_non_finite_history_samples_are_not_statistics():
    report = history_page([["date", "Auto", "NaN", "Infinity", None], ["date2"]], 0, 2)
    assert ": минимум" not in report
    assert "нет данных" in report
