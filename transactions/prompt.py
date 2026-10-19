"""The prompt the model sees is a file, so the documented prompt is the prompt that runs (decision 0002)."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings

PROMPT_PATH = Path(settings.BASE_DIR) / "prompts" / "categorise.md"
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


@dataclass(frozen=True)
class Prompt:
    version: str
    text: str


@lru_cache(maxsize=4)
def load_prompt(path=None):
    raw = Path(path or PROMPT_PATH).read_text(encoding="utf-8")
    header = FRONT_MATTER.match(raw)
    if not header:
        raise ValueError(f"{path or PROMPT_PATH} has no front matter with a version")
    fields = dict(line.split(":", 1) for line in header.group(1).splitlines() if ":" in line)
    version = fields.get("version", "").strip()
    if not version:
        raise ValueError(f"{path or PROMPT_PATH}: front matter has no version")
    return Prompt(version=version, text=raw[header.end():].strip())
