"""Strip ANSI escape codes from strings captured from subprocess output."""

import re

# Matches ANSI escape sequences:
#   \x1B       — ESC byte
#   (?:A|B)    — two possible forms:
#     A: [@-Z\\-_]   — 2-byte sequences like ESC 7, ESC [ (without CSI)
#     B: \[...[@-~]  — CSI sequences: ESC [, optional param bytes (0x30-0x3F),
#                       optional intermediate bytes (0x20-0x2F), final byte (0x40-0x7E)
_ansi_re = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text* and return plain text."""
    return _ansi_re.sub('', text)
