"""Run every recorded firing in tests/captures/ through the parser.

Drop a recording (rohde_mykiln_capture/*.jsonl, redacted if you share it) into
tests/captures/ and these checks run on every poll in it. Add assertions for
specific moments once a bug is understood.
"""
from __future__ import annotations

import json

import pytest

from conftest import CAPTURES

RECORDINGS = sorted(CAPTURES.glob("*.jsonl")) if CAPTURES.is_dir() else []


def _status_items(path):
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("kind") == "status" and isinstance(event.get("raw"), list):
                for item in event["raw"]:
                    if isinstance(item, dict):
                        yield event["time"], item


@pytest.mark.skipif(not RECORDINGS, reason="no recordings in tests/captures yet")
@pytest.mark.parametrize("path", RECORDINGS, ids=lambda p: p.name)
def test_recording_parses(parser, path):
    polls = 0
    for time, item in _status_items(path):
        kiln = parser.parse_kiln(item)
        assert kiln is not None, f"{time}: no kiln id"
        assert not (kiln.is_heating and kiln.is_cooling), time
        if kiln.online and kiln.is_firing:
            assert kiln.temperatures[0] is not None, f"{time}: firing without temperature"
        polls += 1
    assert polls, "recording contains no status responses"
