"""Parser tests with the formats seen so far.

These examples are written by hand. Recorded firings in tests/captures/ are
checked by test_captures.py.
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("173°C", (173.0, "C")),
        ("1250 °C", (1250.0, "C")),
        ("2012°F", (2012.0, "F")),
        ("21,5°C", (21.5, "C")),
        ("-°C", (None, None)),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_temperature(parser, text, expected):
    assert parser.parse_temperature(text) == expected


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("26 hrs 17 mins", 26 * 60 + 17),
        ("1 hr 0 mins", 60),
        ("45 mins", 45),
        ("3 uur 5 minuten", 185),
        ("", None),
        ("-", None),
        (None, None),
    ],
)
def test_duration(parser, text, minutes):
    assert parser.parse_duration(text) == minutes


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("Laatst bijgewerkt: 62 uur geleden", 62 * 3600),
        ("Last updated: 5 minutes ago", 300),
        ("Last updated: 30 seconds ago", 30),
        ("Zuletzt aktualisiert: vor 2 Tagen", 2 * 86400),
        ("Last updated: 1 week ago", 604800),
        ("Online", None),
        (None, None),
    ],
)
def test_age(parser, text, seconds):
    assert parser.parse_age(text) == seconds


def _raw(**overrides):
    raw = {
        "id": 42,
        "zones": 1,
        "is_communicating": True,
        "temperature_1": "873°C",
        "temperature_2": "-°C",
        "temperature_3": "-°C",
        "firing_status": "Heating",
        "kiln_status_summary": "Firing",
        "is_firing": True,
        "is_cooling": False,
        "is_delayed_start": False,
        "program_title": "Glaze 1230",
        "firing_percentage": "57",
        "firing_duration": "5 hrs 12 mins",
        "wifi_bars": 3,
        "firing_id": 9001,
        "comms_status": "Last updated: 1 minute ago",
    }
    raw.update(overrides)
    return raw


def test_parse_kiln_heating(parser):
    kiln = parser.parse_kiln(_raw())
    assert kiln.kiln_id == 42
    assert kiln.online
    assert kiln.temperatures == (873.0, None, None)
    assert kiln.unit == "C"
    assert kiln.status == "Heating"
    assert kiln.is_heating and not kiln.is_cooling
    assert kiln.percentage == 57
    assert kiln.duration_minutes == 312
    assert kiln.last_update_seconds == 60


def test_parse_kiln_cooling(parser):
    kiln = parser.parse_kiln(_raw(is_cooling=True, firing_status="Cooling down"))
    assert kiln.is_cooling and not kiln.is_heating


def test_status_falls_back_to_summary(parser):
    kiln = parser.parse_kiln(_raw(firing_status="", kiln_status_summary="Idle"))
    assert kiln.status == "Idle"


# Formats from a recorded firing (Dutch account, ST310 controller, 24 Nov 2026).

def test_idle_placeholders(parser):
    """Before a firing myKiln sends "-" for status, program and duration."""
    kiln = parser.parse_kiln(_raw(
        is_firing=False, firing_status="-", kiln_status_summary="Inactief", program_title="-",
        firing_percentage="", firing_duration="-", firing_id=None, temperature_1="16°C",
    ))
    assert kiln.status == "Inactief"
    assert kiln.program is None
    assert kiln.percentage is None and kiln.duration_minutes is None
    assert kiln.phase == "idle" and kiln.ramp_rate is None


def test_ramping(parser):
    kiln = parser.parse_kiln(_raw(firing_status="Stoken bij 150 °C/hr", kiln_status_summary="Actief"))
    assert kiln.phase == "heating" and kiln.is_heating and not kiln.is_holding
    assert kiln.ramp_rate == 150


def test_soak_is_holding_not_heating(parser):
    kiln = parser.parse_kiln(_raw(firing_status="Soak", temperature_1="1220°C", firing_percentage=99))
    assert kiln.is_holding and not kiln.is_heating
    assert kiln.phase == "holding" and kiln.ramp_rate is None
    assert kiln.status == "Soak"


def test_cooling_after_program(parser):
    kiln = parser.parse_kiln(_raw(firing_status="Afkoelen", is_cooling=True, firing_percentage=100,
                                  firing_duration="11 hrs 33 mins"))
    assert kiln.phase == "cooling" and not kiln.is_heating and not kiln.is_holding
    assert kiln.ramp_rate is None and kiln.duration_minutes == 693


def test_offline_before_firing(parser):
    kiln = parser.parse_kiln(_raw(
        is_communicating=False, is_firing=False, firing_status="-", kiln_status_summary="Offline",
        temperature_1="-°C", comms_status="Laatst bijgewerkt: 37 uur geleden",
    ))
    assert not kiln.online and kiln.status == "Offline"
    assert kiln.temperatures[0] is None and kiln.last_update_seconds == 37 * 3600


@pytest.mark.parametrize(
    ("text", "rate"),
    [("Stoken bij 60 °C/hr", 60), ("Firing at 100°C/h", 100), ("Heating at 212 °F/hr", 212),
     ("Afkoelen", None), ("Soak", None), ("-", None)],
)
def test_ramp_rate(parser, text, rate):
    assert parser.parse_ramp_rate(text) == rate


def test_delayed_start_phase(parser):
    kiln = parser.parse_kiln(_raw(is_firing=False, is_delayed_start=True))
    assert kiln.phase == "delayed_start"


def test_parse_kiln_without_id(parser):
    assert parser.parse_kiln({"temperature_1": "20°C"}) is None


def test_as_dict_has_derived_fields(parser):
    data = parser.parse_kiln(_raw()).as_dict()
    assert data["is_heating"] is True
    assert data["temperatures"] == [873.0, None, None]


KILN_LIST = """
<div><h3>Garage</h3>
<a href="/kiln_edit/42/">Edit</a>
<img src="/media/kiln_images/abc/TE-80-MCC.png">
<h3> ST310 </h3><p>SN 12345678</p></div>
<div>Unlinked controller area<h3>Spare</h3><a href="/kiln_edit/7/">Edit</a></div>
"""


def test_parse_kiln_list(parser):
    info = parser.parse_kiln_list(KILN_LIST)
    assert list(info) == [42]
    assert info[42].name == "Garage"
    assert info[42].model == "TE 80 MCC"
    assert info[42].controller == "ST310"
    assert info[42].serial == "12345678"
