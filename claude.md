# Project Standards: Python Automation

## Directory Structure
- `/src`: All source code.
- `/logs`: Log files (ignored by git).
- `/data`: Input/Output files.
- `main.py`: Entry point.
- `tasks/`: Individual automation logic.

## Coding Style
- Follow **PEP 8** strictly.
- Use **Type Hinting** for all function signatures.
- Documentation: Every function must have a brief docstring explaining the `Args` and `Returns`.

## Error Management Strategy
- Use `loguru` for all output instead of `print()`.
- Critical failures must raise custom exceptions.
