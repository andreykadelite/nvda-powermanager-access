# User guide

[Русский](../ru/user-guide.md)

PowerManagerII Access works with the Russian edition of Richcomm PowerManagerII 4.1 revision 646. The add-on's labels and dialogs are Russian, even when NVDA uses another language. This guide gives English explanations and the Russian names you will hear.

## Installation

Install NVDA and PowerManagerII first. Open `powerManagerAccess-1.0.0.nvda-addon`, confirm installation in NVDA, and restart NVDA. No separate Python installation or runtime libraries are needed.

If you used a private development build numbered 2.x, install 1.0.0 manually. It is the first public release and keeps the completed accessibility work. Its lower number does not indicate older functionality. Do not run two copies of the add-on together.

The `NVDA` key below means Insert or Caps Lock, according to your NVDA settings.

## Read a screen and choose a tab

Open PowerManagerII and press `F6`. The add-on opens a window with three tabs and places focus on the current tab's contents. Up and Down read its rows.

| Tab you hear | Contents |
| --- | --- |
| Состояние ИБП | UPS status: connection, mains supply, battery, faults, self-test, operating mode, load and charge |
| Текущие измерения | Current measurements and states reported in the source table, with names and units |
| График измерений | An explanation of the graph and buttons for current measurements and saved history |

`Control+Tab` focuses the next tab header; `Control+Shift+Tab` goes back. Arrow keys work on headers too. Focus alone leaves the open page unchanged. Press `Enter`, numpad Enter or `Space` to open the focused tab. `Tab` then moves to its contents.

For example, while reading UPS status, press `Control+Tab` to focus «Текущие измерения». Press `Enter` and then `Tab` to read measurements. If you press Tab without Enter, you return to the status data that is still open. The window title and list label identify the open page.

`F6` switches between the open page's contents and its selected header. `Home` and `End` focus the first and last headers in the add-on's tab windows. Pressing Enter on an already open tab does not reload it. Use `F5` to refresh readings; the selected row is preserved. The caption above the list gives the reading time.

`Escape` closes the tab window and returns to the selected screen in PowerManagerII. Its original screen buttons also open these tabs with Enter or Space. The settings, notification and command-panel tabs use the same manual activation rule. In the original dialogs, Tab visits the selected header as one stop and then goes to the open section's fields.

## Keyboard reference

The shortcuts with the NVDA key work in the original PowerManagerII window, not in the separate windows hosted by NVDA.

| Shortcut | Action |
| --- | --- |
| NVDA+Alt+F1 | Open the extra panel with status, commands, source-window controls and help |
| NVDA+Alt+F2 | Speak UPS status |
| NVDA+Alt+F3 | Open a text report of UPS status |
| NVDA+Alt+F4 | Read the current window's text and tables |
| NVDA+Alt+F5 | Turn status-change announcements on or off |
| NVDA+Alt+F6 | Open the UPS status tab |
| NVDA+Alt+F7 | Open current measurements |
| NVDA+Alt+F8 | Open measurement history; press again within history to read text records |
| F6 | Read the open screen; in the tab window, move between the header and contents |
| F10 or Applications | Open the main menu in the original window; F10 also works in the tab window |
| F1 | Read help for the current window |
| Tab / Shift+Tab | Move to the next / previous available control |
| Control+Tab / Control+Shift+Tab | Focus the next / previous tab header without opening it |
| Enter, numpad Enter or Space | Open the focused tab or activate a button or checkbox |
| Arrow keys on a radio button | Choose another option in its group |
| Escape | Close a dialog without pressing its save button |
| F5 in the add-on's reading windows | Refresh data |
| Control+PageDown / Control+PageUp in text history | Read the next / previous 50 records |

In tab windows, Control+PageDown and Control+PageUp also move between headers without activation. Lists, date fields, calendars and combo boxes keep their normal Windows keyboard behavior. For dates, Left and Right choose a part; Up and Down change it. `Alt+Down` opens a list or calendar. Escape first closes an expanded control.

NVDA's `Control+Alt+Arrow` commands read table cells. You can change add-on shortcuts in NVDA's Input Gestures dialog under PowerManagerII while the original program is focused. The add-on also handles a TabReporter conflict in recognized PowerManagerII windows.

## Settings and notifications

Use F10 to open «Система» (System). Settings have four sections: connection, shutdown, critical events and history recording. Notifications have five: network messages, SMS, email, sound and popup messages.

Choose a header with Control+Tab or the arrow keys, open it with Enter or Space, then use Tab for its fields. Hidden and disabled controls are skipped. The extra panel's «Элементы окна» page lists disabled controls with an explanation, but prevents moving focus to them.

For a critical event, choose the computer action before setting its conditions and delays. In sound notifications, select an event before choosing a sound file. Recipient fields are named for the selected channel, such as email address or mobile number. Password fields are omitted from text reports.

Save changes with the program's own save buttons. Escape closes editing without pressing Save. Merely changing a tab does not save settings.

## UPS schedules

The vendor's «Блок-схема ИБП» menu item opens a task schedule. The add-on calls it «Расписание задач ИБП (Блок-схема ИБП)».

1. Choose a task using arrows on its radio-button group: short test, test until low battery, timed test, shutdown, or shutdown followed by restart.
2. Use Tab to reach the fields for that task. Restart tasks have their own day and time fields.
3. Review the computer-shutdown checkbox, repetition, start time, dates or weekdays.
4. Move to «Добавить задачу» to add the task and review the confirmation. Select a saved row before editing or deleting an existing task.

Enter inside a schedule field does not add a task. The add-on asks you to use the explicit Add or Edit button. These are schedules for real equipment; confirmed tasks can later run automatically.

## History and graphs

Measurement and event history remain readable in the original tables. Their dialogs provide filters, dates, refresh controls and separate deletion windows.

`NVDA+Alt+F8` opens measurement history from the main window. Press it again in history to read text records in pages of 50. Each page includes units and the minimum and maximum of its numeric readings. Statistics describe that page, not the entire database. The history filter selects the period. In graph mode, this command first restores the table.

Page buttons are disabled at the beginning and end. The general window report from `NVDA+Alt+F4` reads at most the first 100 rows of each table. Other rows remain available in the original table; measurement history also has the paged reader.

The current graph is available in the View menu. Its ActiveX component does not expose numeric curve points to NVDA. The graph tab offers «Читать текущие измерения» (read current measurements) and «Открыть историю измерений» (open saved history). Saved records have their own recording interval and are not every point in the live graph. Reopening the selected graph does not restart it.

## Confirmations and errors

Supported test, power, schedule, deletion, UPS beeper and event-clear commands require confirmation when invoked through the add-on. No is selected by default. The checks also cover Enter in a power-delay field and activation through NVDA object navigation.

Before dispatch, the add-on checks that the window, control and reviewed parameters still match. A changed selection or parameter cancels the request. Edit and Delete require a selected record. Rapid duplicate button activation is suppressed.

An open dialog can block an incompatible main-window command. Missing controls and response timeouts produce an explanation. Later keyboard input cancels pending focus restoration, so it does not undo your next navigation step. The add-on's confirmations do not govern commands sent directly by mouse or other software.

## Status-change announcements

`NVDA+Alt+F5` enables a check every five seconds. It announces changes in displayed connection, mains, battery and other statuses, rather than every voltage fluctuation. Press it again to stop. Closing PowerManagerII or restarting NVDA also stops monitoring.

When the connection is not confirmed, numeric readings are marked unavailable. A reading error is announced once, followed by a separate recovery message when reading works again. The add-on reads the program's data; it does not check the physical accuracy of the UPS sensors.

## Help and saved files

The vendor's help opens Windows HTML Help. F6 moves between the contents and article; arrows choose a topic; Alt+F4 closes help. The tested vendor help is mostly English. F1 in PowerManagerII opens the add-on's Russian help.

«Сохранённые файлы» opens Richcomm Appinfo. The add-on names its two lists, empty rows and Close button. Tab moves between them, arrows select records, F1 reads help and Escape closes the window. Restoring real saved documents has not been tested.

## Troubleshooting

If a main-window command is blocked, close the open dialog with Escape and try again. If reading fails, check that PowerManagerII still shows a connection and press F5. Do not change a working UPS connection just to test accessibility.

For an unrecognized control or a focus problem, include your program, NVDA and Windows versions, the exact keys pressed and the words NVDA spoke in a bug report. Remove passwords, recipient addresses and private log entries before attaching diagnostics.

See [test coverage](testing.md) for the verified versions and limits, or the [developer guide](development.md) to build the add-on.
