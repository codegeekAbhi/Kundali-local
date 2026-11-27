"""Offline Vedic chart calculator. Requires pyswisseph."""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from readings import ai_reading, offline_reading

SIGNS = "Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces".split()
NAKSHATRAS = (
    "Ashwini|Bharani|Krittika|Rohini|Mrigashira|Ardra|Punarvasu|Pushya|Ashlesha|"
    "Magha|Purva Phalguni|Uttara Phalguni|Hasta|Chitra|Swati|Vishakha|Anuradha|"
    "Jyeshtha|Mula|Purva Ashadha|Uttara Ashadha|Shravana|Dhanishtha|Shatabhisha|"
    "Purva Bhadrapada|Uttara Bhadrapada|Revati"
).split("|")
DASHA = tuple(zip(
    "Ketu Venus Sun Moon Mars Rahu Jupiter Saturn Mercury".split(),
    (7, 20, 6, 10, 7, 18, 16, 19, 17),
))
NAKSHATRA_WIDTH = 360 / 27
DASHA_YEAR_DAYS = 365.25


def resolve_birth(value, zone_name, fold):
    if "T" not in value:
        raise ValueError("Supply both a birth date and time, e.g. 2000-01-01T12:00.")
    local = datetime.fromisoformat(value)
    if local.tzinfo is not None:
        raise ValueError("Supply a local date and time without a UTC offset.")
    zone = ZoneInfo(zone_name)
    instants = {}
    for index in (0, 1):
        instant = local.replace(tzinfo=zone, fold=index).astimezone(timezone.utc)
        if instant.astimezone(zone).replace(tzinfo=None) == local:
            instants[index] = instant
    if not instants:
        raise ValueError("This local time falls in a clock change gap.")
    if len(set(instants.values())) > 1 and fold is None:
        raise ValueError("This time occurs twice. Use --fold 0 (earlier) or --fold 1 (later).")
    return instants[0 if fold is None else fold]


def print_dasha(birth, moon, as_of, emit):
    index = int(moon / NAKSHATRA_WIDTH) % len(DASHA)
    progress = moon / NAKSHATRA_WIDTH % 1
    lord, years = DASHA[index]
    start = birth - timedelta(days=progress * years * DASHA_YEAR_DAYS)
    emit(f"Birth mahadasha: {lord} ({years * (1 - progress):.2f} years remaining at birth)")
    for offset in range(18):
        period_index = (index + offset) % len(DASHA)
        lord, years = DASHA[period_index]
        end = start + timedelta(days=years * DASHA_YEAR_DAYS)
        if start <= as_of < end:
            emit(f"Mahadasha on {as_of.date()} UTC: {lord}")
            emit(f"Period: {start.date()} to {end.date()} UTC (end exclusive)")
            sub_index, sub_start, sub_end = active_subperiod(period_index, start, end, as_of)
            emit(f"Antardasha: {DASHA[sub_index][0]} ({sub_start.date()} to {sub_end.date()} UTC)")
            inner_index, inner_start, inner_end = active_subperiod(sub_index, sub_start, sub_end, as_of)
            emit(f"Pratyantardasha: {DASHA[inner_index][0]} ({inner_start.date()} to {inner_end.date()} UTC)")
            return " / ".join(DASHA[i][0] for i in (period_index, sub_index, inner_index))
        start = end
    emit("As-of date is outside the available dasha timeline.")


def active_subperiod(parent_index, start, end, as_of):
    elapsed_weight = 0
    sub_start = start
    for offset in range(len(DASHA)):
        index = (parent_index + offset) % len(DASHA)
        elapsed_weight += DASHA[index][1]
        sub_end = start + (end - start) * (elapsed_weight / 120)
        if sub_start <= as_of < sub_end:
            return index, sub_start, sub_end
        sub_start = sub_end
    raise ValueError("Lookup time falls outside the parent dasha period.")


def navamsha_sign(longitude):
    return int(longitude * 3 / 10) % len(SIGNS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("birth", help="Local birth date/time, YYYY-MM-DDTHH:MM")
    parser.add_argument("zone", help="IANA time zone, e.g. Asia/Kolkata")
    parser.add_argument("latitude", type=float)
    parser.add_argument("longitude", type=float, help="East positive, west negative")
    parser.add_argument("--fold", type=int, choices=(0, 1))
    parser.add_argument("--as-of", help="Dasha lookup date (YYYY-MM-DD, midnight UTC)")
    parser.add_argument("--lal-kitab", action="store_true", help="Show house occupancy for a Lal Kitab reading")
    parser.add_argument("--reading", choices=("offline", "ollama", "openai"),
                        help="Add a reading. Without this flag, print the chart only.")
    parser.add_argument("--model", help="Model name for Ollama or OpenAI")
    parser.add_argument("--topic", choices=("overview", "career", "relationships"), default="overview")
    args = parser.parse_args()
    if args.reading in ("ollama", "openai") and not args.model:
        parser.error("--model is required for an AI reading.")
    if not (-90 < args.latitude < 90 and -180 <= args.longitude <= 180):
        parser.error("Supply latitude between -90 and 90 (exclusive) and longitude from -180 to 180.")
    try:
        birth = resolve_birth(args.birth, args.zone, args.fold)
        as_of = (
            datetime.strptime(args.as_of, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if args.as_of else datetime.now(timezone.utc)
        )
    except (ValueError, ZoneInfoNotFoundError, OverflowError) as error:
        parser.error(str(error))

    try:
        import swisseph as swe
    except ImportError:
        parser.exit(1, "Install pyswisseph before running this calculator.\n")

    hour = birth.hour + birth.minute / 60 + birth.second / 3600 + birth.microsecond / 3.6e9
    jd = swe.julday(birth.year, birth.month, birth.day, hour)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL
    bodies = (
        ("Sun", swe.SUN), ("Moon", swe.MOON), ("Mars", swe.MARS),
        ("Mercury", swe.MERCURY), ("Jupiter", swe.JUPITER),
        ("Venus", swe.VENUS), ("Saturn", swe.SATURN), ("Rahu", swe.MEAN_NODE),
    )
    try:
        _, angles = swe.houses_ex(jd, args.latitude, args.longitude, b"W", swe.FLG_SIDEREAL)
        planets = {name: swe.calc_ut(jd, body, flags)[0][0] % 360 for name, body in bodies}
    except swe.Error as error:
        parser.exit(1, f"Ephemeris calculation failed: {error}\n")

    ascendant = angles[0] % 360
    planets["Ketu"] = (planets["Rahu"] + 180) % 360
    print(f"Birth instant: {birth.isoformat()} | Julian day: {jd:.6f}")
    chart_lines = []

    def emit(line):
        chart_lines.append(line)
        print(line)

    emit("Lahiri sidereal zodiac | whole-sign houses | mean lunar nodes")
    d9_lagna = navamsha_sign(ascendant)
    emit(f"{'Point':<12} {'D1 Sign':<12} {'Degree':>8} {'House':>5}  {'D9 Sign':<12} {'House':>5}")
    house_occupants = [[] for _ in SIGNS]
    for name, longitude in {"Ascendant": ascendant, **planets}.items():
        sign_index = int(longitude / 30)
        house = (sign_index - int(ascendant / 30)) % 12 + 1
        d9_sign = navamsha_sign(longitude)
        d9_house = (d9_sign - d9_lagna) % 12 + 1
        emit(f"{name:<12} {SIGNS[sign_index]:<12} {longitude % 30:8.4f} {house:5}  "
              f"{SIGNS[d9_sign]:<12} {d9_house:5}")
        if name != "Ascendant":
            house_occupants[house - 1].append(name)
    moon = planets["Moon"]
    nakshatra = NAKSHATRAS[int(moon / NAKSHATRA_WIDTH)]
    pada = int((moon / NAKSHATRA_WIDTH % 1) * 4) + 1
    emit(f"Moon nakshatra: {nakshatra}, pada {pada}")
    period = print_dasha(birth, moon, as_of, emit) or "outside the available timeline"
    if args.lal_kitab:
        emit("\nLal Kitab reading inputs | D1 whole-sign houses shown by number")
        for number, occupants in enumerate(house_occupants, start=1):
            emit(f"House {number:2}: {', '.join(occupants) or 'Empty'}")

    if args.reading:
        reading = offline_reading(
            SIGNS[int(ascendant / 30)], SIGNS[int(moon / 30)],
            (int(moon / 30) - int(ascendant / 30)) % 12 + 1,
            period, house_occupants, args.lal_kitab, args.topic,
        )
        mode = args.reading
        if mode in ("ollama", "openai"):
            try:
                reading = ai_reading(mode, args.model, args.topic, "\n".join(chart_lines), args.lal_kitab)
            except ValueError as error:
                print(f"\n{error} Showing the offline reading.", file=sys.stderr)
                mode = "offline"
        print(f"\nReading ({mode})")
        print(reading)


if __name__ == "__main__":
    main()
