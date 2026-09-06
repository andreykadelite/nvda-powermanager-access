# PowerManagerII Access 1.0.0

## English

First public release of the NVDA add-on for Richcomm PowerManagerII.

Read UPS status and current measurements as named rows, navigate the program's dialogs and menus from the keyboard, and read measurement history in pages of 50 records. Tab headers use manual activation: arrows and Control+Tab move focus; Enter or Space opens the tab. Supported power, self-test, schedule and deletion commands have confirmations when invoked through the add-on.

Tested with Russian PowerManagerII 4.1 revision 646, PowerManager.exe 1.0.348.273, NVDA 2025.3.3 32-bit and Windows 11 25H2. The interface is Russian; the user and developer documentation is available in English and Russian.

Download `powerManagerAccess-1.0.0.nvda-addon`, open it in NVDA and restart NVDA. Start with F6 in PowerManagerII. The source ZIP contains code, documentation, unit tests and build tools. `SHA256SUMS.txt` contains checksums for both archives.

Graph points are not exposed by the vendor's ActiveX control. Current measurements and saved history are available separately. Real shutdown, discharge, self-test execution, notification sending and record deletion were not performed during accessibility testing.

Earlier version numbers belonged to private development builds. Install 1.0.0 manually if you used one of those builds.

## Русский

Первый публичный выпуск дополнения NVDA для Richcomm PowerManagerII.

Дополнение выводит состояние и показания ИБП в именованных строках, открывает меню и диалоги с клавиатуры, читает историю измерений по 50 записей. Стрелки и Control+Tab перемещают фокус между заголовками, Enter и пробел открывают вкладку. Поддерживаемые команды питания, самотеста, расписания и удаления требуют подтверждения при выполнении через дополнение.

Проверены русская PowerManagerII 4.1 revision 646, PowerManager.exe 1.0.348.273, NVDA 2025.3.3 32-разрядная и Windows 11 25H2. Интерфейс дополнения русский, документация пользователя и разработчика есть на двух языках.

Скачайте `powerManagerAccess-1.0.0.nvda-addon`, откройте его в NVDA и перезапустите NVDA. В PowerManagerII начните с F6. ZIP с исходниками содержит код, документацию, тесты и сборщик. Контрольные суммы обоих архивов записаны в `SHA256SUMS.txt`.

График ActiveX не передаёт числовые точки. Для чтения есть текущие измерения и отдельная история. Настоящее выключение, разряд, выполнение самотеста, отправка уведомлений и удаление записей при испытаниях доступности не выполнялись.

Прежние номера относились к частным сборкам разработки. Если вы пользовались такой сборкой, установите 1.0.0 вручную.
