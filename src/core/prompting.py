from __future__ import annotations

from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def render_prompt(template_name: str, **values) -> str:
    template_path = PROMPTS_DIR / template_name
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.safe_substitute(**values).strip()
