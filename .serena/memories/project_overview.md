# Project Overview: V8Parse

**Purpose**: Parse multi-protocol communication logs (hex plaintext) into structured data for analysis. Protocols include V8, Xiaoju, Yunwei, Sinexcel. Configurable format files drive data-field parsing; logs are grouped by timestamps and frame headers.

**Tech Stack**: Python 3.7+; standard library only; Windows/Linux/macOS support.

**Architecture**:
- `src/base_protocol.py`: BaseProtocol provides common file extraction (time regex + frame head) and message parsing pipeline using `ProtocolConfig(head_len, tail_len, frame_head)`.
- `src/cmdformat.py`: Reads format files (`resources/format_*.txt`), supports fixed length, repeated fields (Nn), for-group loops, and variable-length loops; loads command filter and alarm/stop dictionaries.
- `src/field_parser.py`: Field decoding (BCD, ASCII, bitfields, CP56Time2a, datetime builders, alarm bit mapping), multi-bit/byte parsing.
- Protocol implementations: `src/v8_protocol.py`, `src/xiaoju_protocol.py`, legacy `src/yunwei_portocol.py`, `src/sincexcel_portocol.py`.
- Entry: `main.py` uses `ProtocolType` and a factory to instantiate protocol classes; legacy `v8_run.py`, `sinexcel_run.py`, `yunwei_run.py` call older modules.

**Key Resources**: `resources/format_mcu_ccu.txt`, `format_xiaoju.txt`, `format_yunwei.txt`, `format_sinexcel.txt`, `filter.txt`, `alarm.conf`.

**Entrypoints**:
- Recommended: `python main.py` (set `PROTOCOL_TYPE` in file; currently V8/XIAOJU mapped).
- Legacy: `python v8_run.py`, `python sinexcel_run.py`, `python yunwei_run.py`.

**Notable Design**: OOP with strategy/template; data-field parsing is configuration-driven via format files; head/tail sizes and frame head are in `ProtocolConfig`.

**Gaps for config-only operation**: Head-field extraction (cmd/sequence/etc.), time regex, grouping rules, and cmd aliases currently live in protocol classes; could be centralized and driven by a protocol schema config for non-developer operation.
