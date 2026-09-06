# Test coverage

[Русский](../ru/testing.md) | [User guide](user-guide.md)

## Verified environment

Testing used Richcomm PowerManagerII 4.1 revision 646 with a Russian interface, PowerManager.exe file version 1.0.348.273, NVDA 2025.3.3 32-bit, and Windows 11 25H2. Development and the local unit-test run used Python 3.14.7; the add-on source is checked against Python 3.11 syntax.

The completed accessibility code underwent 88 unit tests and three successful live test series before the first public release: 100 tab and reading scenarios, 91 general scenarios, and 63 follow-up scenarios. The general series included 159 verified forward and reverse Tab transitions. Saved-files navigation and a further 19-step main-window cycle were checked separately.

These tests ran on development builds. Public version 1.0.0 keeps that accessibility code and starts the public version history. Release preparation changes version metadata, documentation, licensing presentation and build tooling. Release packaging adds three unit tests, bringing the local total to 91 passing tests. Repository CI checks the unit tests and packaging; it does not control a real UPS or prove live accessibility by itself.

## What the live tests covered

- Focus and selection stay separate on all three reading tabs, four settings sections, five notification sections and four extra-panel tabs.
- Enter, numpad Enter and Space open a focused tab. Arrow keys, Control+Tab and reverse navigation leave the source screen unchanged until activation.
- The reading windows expose 8 status rows, 15 current table rows and 6 graph explanations in the tested connected state.
- Tab, F6, refresh with preserved row, Escape, Alt+Tab, help, menus and both graph buttons work through the running NVDA.
- A Tab sent 40 milliseconds after opening a window and subsequent list reading do not trigger a later jump back to the header.
- Settings, notifications, recipients, event and measurement histories, filtering, the deletion dialog, ratings and About have named controls and verified Tab navigation.
- All 3 power options, 4 self-test options and 5 schedule types expose their related fields. Confirmations were opened and cancelled.
- Unit tests cover missing selection, changed parameters, duplicate dispatch, timeouts, stale data, superseded requests and focus changes after later input.

## Not verified

The tests did not shut down equipment, discharge batteries, execute a real UPS self-test, save schedules, send notifications or delete user records. Actual restoration of saved documents, a physical braille display and a remote UPS were not tested.

The ActiveX graph does not expose numeric curve points through MSAA, the accessibility interface used by the component. Current table values and saved history are available, but they cannot reconstruct every point in that graph.

Other PowerManagerII versions, an English PowerManagerII interface, later NVDA releases and other add-on combinations need their own checks. Passing tests is not a guarantee that every configuration is free of defects.

## Manual regression checklist

1. Install the built add-on and restart NVDA. Open PowerManagerII and confirm that program and control names are spoken.
2. Press F6. Read the current tab's contents. Move focus to another header with Control+Tab and verify that the open page and source screen remain unchanged.
3. Press Enter, Tab and Down. Verify the new page's name, data and actual focus. Repeat with Space, numpad Enter and reverse navigation.
4. Refresh after selecting a later row. Try a fast Tab after opening. Switch applications with Alt+Tab, return, and ensure no delayed callback overrides the next action.
5. Test the graph's current-measurement and history buttons. Read history pages, check page boundaries and close both reading windows.
6. Visit every settings and notification header. Focus alone must not open a section; Enter or Space must. Tab should reach its fields.
7. Read every menu and walk both directions through each dialog. Exercise radio options without pressing an execution or save button.
8. Open a protected command's confirmation and cancel it. Verify that no command ran and focus returned correctly.
9. Read F1 help and the status/window reports. Turn status monitoring on and off. Check NVDA's log for add-on exceptions.

Record exact keys, focus, spoken text, selected tab and source screen. Use a test profile and suitable test equipment for any separately authorized hardware test. Keep raw logs private; public reports should contain only the details needed to reproduce the problem.
