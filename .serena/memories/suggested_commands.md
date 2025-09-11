# Suggested Commands (Windows / PowerShell)

## Run
- python --version
- py -3 main.py  # or: python main.py (ensure cwd is project root)
- py -3 v8_run.py
- py -3 sinexcel_run.py
- py -3 yunwei_run.py

## Edit Protocol Type
- Open main.py and set `PROTOCOL_TYPE = ProtocolType.V8` (or XIAOJU).

## Tests (if added)
- py -3 -m pytest src/test.py -v

## Lint/Format (manual guidance; no config included here)
- (Optional) Install black: `py -3 -m pip install black`
- Run: `py -3 -m black .`

## Utilities (PowerShell)
- Get-ChildItem
- Set-Location D:\work\ubuntu_share\v8parse

## Logs & Output
- Place input logs at project root: `v8_com.log`, `xiaoju.log`, `yunwei.log`, `sincexcel.csv`
- Parsed output: `parsed_log/parsed_net_log_YYYY-MM-DD HH-MM-SS.txt`
