"""Load parser.py on its own, so the tests need neither Home Assistant nor aiohttp."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "custom_components" / "rohde_mykiln" / "parser.py"
CAPTURES = Path(__file__).resolve().parent / "captures"


def _load():
    spec = importlib.util.spec_from_file_location("mykiln_parser", PARSER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_PARSER = _load()


@pytest.fixture
def parser():
    return _PARSER
