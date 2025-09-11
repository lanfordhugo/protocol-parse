# Task Completion Checklist

- Code builds and runs: `py -3 main.py` (or specific run script) without errors
- If protocol mapping updated: verify `get_protocol_class` includes the protocol
- Input logs present at project root with correct filenames
- `resources/filter.txt` set appropriately or empty for all cmds
- Parsing produces files under `parsed_log/` with expected content
- If touching parsing logic: add/update `src/test.py` tests and run `pytest`
- Optional: run formatter (`black .`) and ensure no obvious lint/type issues
- Update README or usage docs when behavior or commands change
