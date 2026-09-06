# PowerManagerII Access

[Русский](README.ru.md) | [User guide](docs/en/user-guide.md) | [Developer guide](docs/en/development.md)

PowerManagerII Access is an NVDA add-on for Richcomm PowerManagerII, a Windows application for monitoring and managing an uninterruptible power supply (UPS). It adds keyboard navigation, names controls that NVDA otherwise cannot identify, and presents UPS readings as text.

The first public release is **1.0.0**. The add-on's spoken labels and dialogs are in Russian. Documentation is available in English and Russian; an English interface is not included in this release.

## What you can do

- Read connection status, battery charge, load, voltage, frequency and other values reported by PowerManagerII.
- Move between tab headers without opening them. Press Enter or Space to open the focused tab, then Tab to read its contents.
- Use menus, settings, notifications, UPS task schedules and history dialogs from the keyboard.
- Read measurement history in pages of 50 records, with the minimum and maximum values for each page.
- Hear changes in the displayed UPS status when monitoring is enabled.
- Review and cancel confirmations before supported power, test, schedule and deletion commands run through the add-on.

The graph component does not expose its numeric points to NVDA. The add-on provides current measurements and saved history as separate ways to read the data.

## Install and start

1. Download `powerManagerAccess-1.0.0.nvda-addon` from [Releases](../../releases/latest).
2. Open the file, accept the installation in NVDA, and restart NVDA.
3. Open PowerManagerII and press `F6` to read the current screen.
4. Use `Control+Tab` to focus another tab. Press `Enter`, then `Tab`, to read it.

Arrow keys read the list. `F5` refreshes the readings and keeps your row. `Escape` returns to PowerManagerII. Python is not required to use the add-on.

## Tested versions

| Component | Tested configuration |
| --- | --- |
| PowerManagerII | Richcomm 4.1 revision 646, Russian interface |
| PowerManager.exe file version | 1.0.348.273 |
| NVDA | 2025.3.3, 32-bit |
| Windows | Windows 11 25H2 |

The manifest requires NVDA 2025.3 and declares testing through the 2025.3 series. Other PowerManagerII builds and later NVDA versions need separate testing. See [test coverage and limits](docs/en/testing.md).

## Build or contribute

On Windows with Python 3.11 or later:

```powershell
.\tools\bootstrap.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\build.py
```

The build creates the add-on, a source archive and SHA-256 checksums in `dist`. The [developer guide](docs/en/development.md) covers dependencies, code layout, checks and release preparation. Please use the [issue forms](../../issues/new/choose) to report a reproducible problem.

## License

GPL-2.0-only. See [LICENSE](LICENSE). NVDA and PowerManagerII are separate products and are not included in this repository. This add-on is an independent project.
