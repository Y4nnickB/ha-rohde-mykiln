"""Replay a myKiln recording (rohde_mykiln_capture/*.jsonl) through the current parser.

Shows, per poll, what changed in the raw myKiln response and in what the
integration makes of it, so a sensor that "did not respond" can be traced to
either myKiln or our parsing. Needs only the Python standard library.

    python tools/replay_capture.py recording.jsonl            # timeline of changes
    python tools/replay_capture.py recording.jsonl --raw      # include raw field changes
    python tools/replay_capture.py recording.jsonl --csv out.csv   # one row per poll
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

PARSER = Path(__file__).resolve().parents[1] / "custom_components" / "rohde_mykiln" / "parser.py"


def load_parser():
    spec = importlib.util.spec_from_file_location("mykiln_parser", PARSER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


parser = load_parser()

COLUMNS = (
    "online",
    "phase",
    "ramp_rate",
    "is_firing",
    "is_heating",
    "is_holding",
    "is_cooling",
    "is_delayed_start",
    "status",
    "program",
    "percentage",
    "duration_minutes",
    "temperatures",
    "comms_text",
    "last_update_seconds",
)


def read_lines(path: Path) -> list[dict[str, Any]]:
    events = []
    with path.open(encoding="utf-8") as file:
        for number, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as err:
                print(f"line {number}: not valid JSON ({err}), skipped", file=sys.stderr)
    return events


def summarize(kiln) -> dict[str, Any]:
    data = kiln.as_dict()
    return {key: data[key] for key in COLUMNS}


def changes(old: dict[str, Any] | None, new: dict[str, Any]) -> list[str]:
    old = old or {}
    return [
        f"{key}: {old.get(key)!r} -> {new.get(key)!r}"
        for key in sorted(set(old) | set(new))
        if old.get(key) != new.get(key)
    ]


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("recording", type=Path)
    args.add_argument("--raw", action="store_true", help="also show raw field changes")
    args.add_argument("--csv", type=Path, help="write one row per poll and kiln")
    opts = args.parse_args()

    events = read_lines(opts.recording)
    previous_parsed: dict[int, dict[str, Any]] = {}
    previous_raw: dict[int, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    polls = 0

    for event in events:
        time = event.get("time", "?")
        kind = event.get("kind")
        if kind == "status":
            if not isinstance(event.get("raw"), list):
                print(f"{time}  STATUS unexpected format: {event.get('raw')!r:.200}")
                continue
            polls += 1
            for item in event["raw"]:
                if not isinstance(item, dict):
                    continue
                kiln = parser.parse_kiln(item)
                if kiln is None:
                    print(f"{time}  kiln without id: {item!r:.200}")
                    continue
                parsed = summarize(kiln)
                lines = changes(previous_parsed.get(kiln.kiln_id), parsed)
                if opts.raw:
                    raw = {k: v for k, v in item.items()}
                    lines += [f"raw.{line}" for line in changes(previous_raw.get(kiln.kiln_id), raw)]
                    previous_raw[kiln.kiln_id] = raw
                if lines:
                    print(f"{time}  kiln {kiln.kiln_id}")
                    for line in lines:
                        print(f"    {line}")
                previous_parsed[kiln.kiln_id] = parsed
                rows.append({"time": time, "kiln": kiln.kiln_id, **parsed, "raw": json.dumps(item)})
        elif kind in ("error", "login", "session_expired"):
            details = {k: v for k, v in event.items() if k not in ("time", "kind")}
            print(f"{time}  {kind.upper()} {details}")
        elif kind == "kiln_list":
            found = event.get("parsed")
            print(f"{time}  KILN LIST {'error ' + event['error'] if 'error' in event else found}")
        elif kind == "start":
            print(f"{time}  START {event}")

    print(f"\n{polls} polls replayed from {opts.recording}")
    if opts.csv and rows:
        with opts.csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows)} rows to {opts.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
