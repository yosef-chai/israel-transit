"""The translation files must stay in step with strings.json.

Home Assistant falls back to the raw key for anything a language file lacks,
so a key added to strings.json and forgotten in he.json shows up in the UI as
"component.israel_transit.triggers.arrival.name" -- for every Hebrew user.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent / "custom_components" / "israel_transit"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _flatten(node: Any, prefix: str = "") -> dict[str, str]:
    if isinstance(node, dict):
        flat: dict[str, str] = {}
        for key, value in node.items():
            flat.update(_flatten(value, f"{prefix}{key}."))
        return flat
    return {prefix.rstrip("."): str(node)}


def _load(path: Path) -> dict[str, str]:
    return _flatten(json.loads(path.read_text(encoding="utf-8")))


SOURCE = _load(ROOT / "strings.json")


def test_english_is_strings_json() -> None:
    assert _load(ROOT / "translations" / "en.json") == SOURCE


@pytest.mark.parametrize("language", ["he"])
def test_every_key_is_translated(language: str) -> None:
    translated = _load(ROOT / "translations" / f"{language}.json")

    assert set(translated) == set(SOURCE)
    for key, text in SOURCE.items():
        # A missing {stop_code} is a message that silently drops the stop.
        assert set(PLACEHOLDER.findall(translated[key])) == set(
            PLACEHOLDER.findall(text)
        ), key
