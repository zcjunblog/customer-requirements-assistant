"""Shared bounded I/O; no network access or shell execution."""
import json
from pathlib import Path

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SOURCE_CHARS = 200_000
MAX_TOTAL_CHARS = 500_000
MAX_FILES = 20


def load_json(path):
    p = Path(path)
    if p.stat().st_size > 12 * 1024 * 1024:
        raise ValueError('JSON 超过 12 MiB，请分批处理。')
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save_json_new(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def safe_text(value):
    # XML 1.0 cannot encode these control characters; retain tabs and newlines.
    return ''.join(c for c in str(value) if c in '\t\n\r' or
                   (0x20 <= ord(c) <= 0xD7FF) or (0xE000 <= ord(c) <= 0xFFFD) or
                   (0x10000 <= ord(c) <= 0x10FFFF))


def skill_version():
    return (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
