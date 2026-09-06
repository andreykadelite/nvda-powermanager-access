# Developer guide

[Русский](../ru/development.md) | [User guide](user-guide.md)

## Requirements

Build and test on Windows with Python 3.11 or later and Git. The tested NVDA runtime uses 32-bit Python 3.11; keep add-on code compatible with that version. The development environment used Python 3.14.7. NVDA supplies wxPython and its own modules at runtime, so do not install a separate wxPython into NVDA.

`requirements-dev.txt` pins four packages: ConfigObj for the manifest, Markdown for documentation, pytest for tests and Ruff for code checks. PowerManagerII and NVDA are needed for live testing, but not for the unit tests or build. GitHub CLI is only needed to publish from the command line.

## Set up and build

From the repository root in PowerShell:

```powershell
.\tools\bootstrap.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check addon tests tools/build.py tools/check_docs.py
.\.venv\Scripts\python.exe tools/check_docs.py
.\.venv\Scripts\python.exe tools/build.py
```

If PowerShell blocks scripts, use `python -m venv .venv` and then `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`. No execution-policy change is required.

The build writes three files in `dist`: the `.nvda-addon` installer, a source ZIP and `SHA256SUMS.txt`. The installer includes Python source, the control map, the license and offline documentation in both languages. Users need only the installer.

ZIP entries use a fixed timestamp and sorted paths, so identical input files produce identical archives in the same build environment. The builder checks Python 3.11 syntax, manifest fields, archive contents and ZIP integrity. Run `.\.venv\Scripts\python.exe -O tools/build.py` in the same environment to verify that checks also work when Python assertions are disabled.

## Code layout

| Path | Responsibility |
| --- | --- |
| `addon/appModules/powermanager/__init__.py` | NVDA events, gestures, control overlays and command checks |
| `native.py` | Win32 window discovery and bounded messages to the program |
| `model.py`, `views.py`, `reports.py` | Status, current readings and history text |
| `labels.py`, `dialog_map.json` | Control names, dialog signatures and navigation order |
| `manual_tabs.py`, `view_dialog.py`, `dialogs.py` | Accessible reading windows and manual tab activation |
| `help.py` | Context help spoken by the add-on |
| `addon/appModules/appinfo.py` | Richcomm's separate saved-files window |
| `docs/en`, `docs/ru` | Documentation sources |
| `tests` | Unit tests with NVDA stubs and mocked program controls |

The paths without a directory prefix are under `addon/appModules/powermanager`. The add-on reads windows in the recognized PowerManagerII process. It does not talk directly to the UPS hardware or edit the vendor's configuration files.

## Change navigation safely

Keep a tab's focused header separate from its selected page. Arrow keys and Control+Tab must not issue a page command. Enter and Space commit the choice. Tab goes to the open page, including when focus was on an inactive header.

Delayed focus work must respect later user input, the foreground window and the actual Windows focus. Do not set a guessed NVDA focus to hide a failure in Windows. The manual notebook uses `TCS_BUTTONS` and `TCM_SETCURFOCUS` so native focus and selection can differ.

Match dialog signatures before naming or activating controls. Keep timeouts and bounds on table reads. Never expose old hidden values as fresh measurements; require confirmed connection status before treating numeric readings as available.

Power, self-test, schedule and deletion actions must preserve the confirmation path and recheck the reviewed parameters. Unit tests mock dispatch; do not connect test code to real equipment to exercise the positive branch.

## Test a change

Run the unit tests and code checks first. Build the installer and install it in a separate NVDA test profile where possible. Keep the running NVDA log available to investigate exceptions, but remove private content before sharing it.

Use the manual checklist in [test coverage](testing.md). Test actual key presses and compare NVDA's reported control with the real Windows focus. Walking a list of controls in code does not prove that keyboard navigation works.

Live inspection scripts and raw logs from the original workstation are intentionally excluded. The public repository includes the unit tests and a manual checklist that can be used on another installation. Do not distribute the vendor's executables, personal configuration, recipient lists or debug hooks.

## Documentation and translations

Edit Markdown under `docs/en` and `docs/ru`, then build. The builder creates `addon/doc/en` and `addon/doc/ru`; do not edit the generated HTML by hand. Both languages need matching instructions and test limits.

Version 1.0.0 has Russian runtime labels and context help. English documentation does not imply an English interface. A future interface translation needs NVDA's add-on translation support and live tests for each supported PowerManagerII language.

## Prepare a release

1. Set the version in `addon/manifest.ini` and update the release notes, changelog and download filenames in the documentation.
2. Run tests, documentation checks and the build. Inspect the source archive and ensure it contains no private files.
3. Commit the reviewed files. CI runs on Windows with Python 3.11 and 3.14, then uploads build artifacts for inspection.
4. Use `tools/publish.ps1` to create the public repository if needed, push the commit, wait for CI, tag it and publish the three release files. The script requires an authenticated GitHub CLI and a clean working tree.

Do not lower an existing public release number. Version 1.0.0 starts the public release history; earlier numbers were local development builds.

## References

- [NVDA developer guide for 2025.3.3](https://download.nvaccess.org/releases/2025.3.3/documentation/developerGuide.html)
- [NVDA source for 2025.3.3](https://github.com/nvaccess/nvda/tree/release-2025.3.3)
- [Windows tab focus](https://learn.microsoft.com/en-us/windows/win32/controls/tcm-setcurfocus)
- [Windows tab styles](https://learn.microsoft.com/en-us/windows/win32/controls/tab-control-styles)
