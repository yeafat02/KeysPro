# KeysPro

KeysPro is a Windows desktop utility that converts structured key records from a
UTF-8 text file into a normalized text format. It provides file browsing,
drag-and-drop input, live processing progress, duplicate detection, invalid-record
reporting, selectable output folders, and timestamped output files.

The application is built with Python and CustomTkinter. A standalone Windows EXE
can be distributed to end users without requiring Python to be installed.

## Features

- Modern CustomTkinter interface with System, Light, and Dark themes
- Fixed, centered `1060 x 620` application window
- Input selection using Browse or drag and drop
- Separate output-folder selection
- Background processing so the interface remains responsive
- Live progress, activity messages, and converted-output preview
- Duplicate TID detection; the first occurrence is retained
- Invalid records are reported and skipped without stopping the conversion
- Atomic output writing to avoid incomplete result files
- Timestamped, collision-safe output filenames
- Rotating application logs with detailed error information
- High-DPI-aware Windows layout
- Single-file, windowed PyInstaller build

## End-user requirements

The standalone build supports:

- Windows 10 or Windows 11
- 64-bit Windows
- No Python installation required

When a release is available, download `KeysPro.exe` from the GitHub Releases page
and double-click it. A code-signing certificate is not currently applied, so
Windows SmartScreen may display a warning on a new machine.

## Using the application

1. Enter the MID.
2. Enter the numeric Index.
3. Browse for a `.txt` input file or drag the file into the application window.
4. Select the output folder.
5. Select **Process File** or press `Ctrl+Enter`.
6. Review the progress, duplicate/invalid counts, and converted-output preview.
7. Select **Open Output File** after the conversion completes.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Browse for an input file |
| `Ctrl+Enter` | Start processing |
| `Ctrl+L` | Return to the input screen when processing is not active |

## Input format

Input files must use UTF-8 or UTF-8 with BOM encoding. Empty lines are ignored.
Each non-empty record must follow this format:

```text
50047171 "id 214667" keyval="CC9E89D86A989DA1D6E9160B800E9B7B" checkval="1574E3"
```

Whitespace between fields may vary. The fields are validated as follows:

| Field | Rule |
|---|---|
| TID | Numeric; used for duplicate detection and output |
| `id` | Numeric; validated but not included in output |
| `keyval` | Exactly 32 hexadecimal characters |
| `checkval` / KCV | Exactly 6 hexadecimal characters |
| MID | 1-15 English letters or numbers; entered in the UI |
| Index | Numeric; entered in the UI |

Hexadecimal values are normalized to uppercase in the output.

### Example input

```text
50047171 "id 214667" keyval="CC9E89D86A989DA1D6E9160B800E9B7B" checkval="1574E3"
50047172 "id 214668" keyval="AABBCCDDEEFF00112233445566778899" checkval="89ABCD"
50047172 "id 214670" keyval="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF" checkval="999999"
INVALID LINE HERE
```

With MID `ABC123` and Index `1`, the first two records are converted. The second
`50047172` record is skipped as a duplicate, and the invalid record is reported.

## Output format

Each valid, unique record is written on one line:

```text
"MID","TID","Index","KEYVAL","CHECKVAL",""
```

Example:

```text
"ABC123","50047171","1","CC9E89D86A989DA1D6E9160B800E9B7B","1574E3",""
"ABC123","50047172","1","AABBCCDDEEFF00112233445566778899","89ABCD",""
```

Output filenames include the local date and time:

```text
input_converted_20260627_214530.txt
```

If the name already exists, KeysPro adds `_01`, `_02`, and so on. Existing output
files are never intentionally overwritten.

## Development requirements

- Windows 10 or Windows 11
- Python 3.12 or newer
- Visual Studio Code with the Microsoft Python extension recommended

## Development setup

Run these commands from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

Using the virtual-environment Python directly avoids PowerShell activation-policy
issues.

## Running from source

```powershell
.\.venv\Scripts\python.exe -m keyspro
```

For Visual Studio Code:

1. Open the repository folder.
2. Run **Python: Select Interpreter** from the Command Palette.
3. Select `.venv\Scripts\python.exe`.
4. Press `F5` and select **Run KeysPro**, or open `src\keyspro\app.py` and use the
   Python Run button.

The committed `.vscode` configuration supplies the correct `src` import path.

## Quality checks

Run the complete automated test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run static checks:

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
```

Verify that every Python module compiles:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
```

## Building the standalone EXE

The build script runs the tests and Ruff checks before invoking PyInstaller. A
failed quality check stops the build.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

The generated executable is:

```text
dist\KeysPro.exe
```

Build characteristics:

- Single executable (`one-file`)
- Windowed application with no console window
- Bundled Python runtime
- Bundled CustomTkinter and tkinterdnd2 resources
- Target architecture matches the Python interpreter used for the build

The current build environment produces a 64-bit Windows executable. Building a
32-bit executable requires a separate 32-bit Python environment.

## Publishing a GitHub release

The `dist` directory is intentionally ignored by Git. Publish the EXE as a GitHub
Release asset instead of committing it to the source repository.

Recommended release procedure:

1. Update the application version in `pyproject.toml`, `src/keyspro/__init__.py`,
   and `src/keyspro/config.py`.
2. Run the test, lint, and compilation commands.
3. Run the clean build script.
4. Launch `dist\KeysPro.exe` on a clean Windows machine.
5. Test Browse, drag and drop, conversion, output opening, and theme switching.
6. Generate a SHA-256 checksum:

   ```powershell
   Get-FileHash .\dist\KeysPro.exe -Algorithm SHA256
   ```

7. Create a version tag and GitHub Release.
8. Upload `KeysPro.exe` and include its SHA-256 checksum in the release notes.

## Project structure

```text
KeysPro/
|-- .vscode/                 VS Code interpreter and launch configuration
|-- scripts/
|   `-- build.ps1            Verified production-build script
|-- src/keyspro/
|   |-- __main__.py          Module entry point
|   |-- app.py               Application bootstrap and DPI handling
|   |-- config.py            Per-user configuration and data paths
|   |-- logger.py            Rotating file logging
|   |-- models.py            Typed domain and progress models
|   |-- processor.py         Validation, parsing, and conversion service
|   `-- ui.py                CustomTkinter screens and dialogs
|-- tests/
|   `-- test_processor.py    Parser and conversion tests
|-- KeysPro.spec             PyInstaller one-file specification
|-- pyproject.toml           Package metadata and Ruff configuration
|-- requirements.txt         Runtime dependencies
`-- requirements-dev.txt     Build and development dependencies
```

The conversion logic is isolated from the UI, making it independently testable.
Processing runs on a worker thread, while UI updates are delivered through a
thread-safe queue.

## Logs and troubleshooting

Application logs are stored at:

```text
%LOCALAPPDATA%\KeysPro\logs\keyspro.log
```

Logs rotate at approximately 2 MB, with five backup files retained.

### `ModuleNotFoundError: No module named 'keyspro'`

Select `.venv\Scripts\python.exe` in VS Code and install the project in editable
mode:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

### PowerShell blocks `build.ps1`

Use the documented process-local command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

This does not permanently change the system execution policy.

### Input file encoding error

Save the input as UTF-8 or UTF-8 with BOM. Legacy ANSI encodings are not accepted.

### Output file cannot be created

Choose an existing folder where the current Windows user has write permission.
Close the output file if another application has locked it, then process again.

### Windows SmartScreen warning

The application is currently unsigned. For commercial distribution, sign the EXE
with a trusted Windows code-signing certificate.

## Data and privacy

KeysPro processes files locally. It does not upload input, output, MID, keys, or
KCV values to a server. Detailed operational errors are written only to the local
application log.

## Creator

Innovated by **Md. Yeafat**  
Email: `yeafathossain@gmail.com`

## License

No license file is currently included. Add an appropriate license before public
redistribution or external contributions.
