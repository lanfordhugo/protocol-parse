# Code Style and Conventions

- Follow PEP 8 (naming, imports, line length) and PEP 257 docstrings where applicable.
- Type hints are used in core modules (e.g., `BaseProtocol` signatures), prefer adding annotations for new code.
- Design patterns: Strategy/Template (protocol subclasses), Factory (`get_protocol_class`), configuration-driven field parsing via format files.
- Avoid mixing tabs/spaces; match existing formatting.
- Field parsing should be expressed via `resources/format_*.txt` instead of bespoke code when possible.
- Keep protocol-specific logic minimal; prefer shared logic in `BaseProtocol` and declarative formats.
