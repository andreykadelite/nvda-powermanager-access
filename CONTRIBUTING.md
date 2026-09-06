# Contributing

[Developer guide](docs/en/development.md) | [Руководство разработчика](docs/ru/development.md)

For a bug report, include the program, NVDA and Windows versions, exact key presses, expected behavior and the words NVDA spoke. State whether focus moved or a page actually opened. Do not attach credentials, recipient lists or unredacted logs.

For a code change, describe the visible behavior and the checks you ran. Keep tests focused on behavior and failure cases. Run pytest, Ruff, the documentation check and the build before opening a pull request. Update both language guides when keys or workflows change.

Live UPS operations need a separate test plan and suitable equipment. Do not execute them just to prove that a button is accessible. See the [manual checklist](docs/en/testing.md).

Contributions are distributed under this repository's GPL-2.0-only license.

## По-русски

В обращении укажите версии программы, NVDA и Windows, последовательность клавиш, ожидаемый результат и слова NVDA. Уточните, переместился фокус или открылась другая страница. Не прикладывайте пароли, списки получателей и журналы с личными данными.

В запросе на изменение опишите поведение для пользователя и выполненные проверки. Перед отправкой запустите pytest, Ruff, проверку документации и сборку. Если меняются клавиши или порядок действий, обновите обе инструкции.

Проверяйте аппаратные команды только по отдельному плану на подходящем оборудовании. Доступность кнопки можно проверить без её выполнения. Участие в проекте предполагает распространение изменений по лицензии GPL-2.0-only.
