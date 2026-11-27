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


def print_dasha(birth, moon, as_of, emit, timeline=0):
    index = int(moon / NAKSHATRA_WIDTH) % len(DASHA)
    progress = moon / NAKSHATRA_WIDTH % 1
    lord, years = DASHA[index]
    start = birth - timedelta(days=progress * years * DASHA_YEAR_DAYS)
    emit(f"Birth mahadasha: {lord} ({years * (1 - progress):.2f} years remaining at birth)")
    if as_of < birth:
        emit("As-of date precedes birth.")
        return None
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
            if timeline:
                emit(f"Upcoming Vimshottari boundaries (UTC, {timeline} days):")
                limit = as_of + timedelta(days=timeline)
                cursor = as_of
                count = 0
                while cursor < limit:
                    active = active_dasha_sequence(period_index, start, cursor)
                    if active is None:
                        break
                    sequence, boundary = active
                    if count:
                        emit(f"  {cursor.isoformat(timespec='seconds')}  {sequence}")
                    cursor = boundary
                    count += 1
                if count <= 1:
                    emit("  No changes within this window.")
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


def active_dasha_sequence(first_index, start, instant):
    for offset in range(len(DASHA) * 2):
        index = (first_index + offset) % len(DASHA)
        end = start + timedelta(days=DASHA[index][1] * DASHA_YEAR_DAYS)
        if start <= instant < end:
            antar, antar_start, antar_end = active_subperiod(index, start, end, instant)
            inner, _, inner_end = active_subperiod(antar, antar_start, antar_end, instant)
            return " / ".join(DASHA[i][0] for i in (index, antar, inner)), inner_end
        start = end
    return None


def julian_day(swe, instant):
    hour = (instant.hour + instant.minute / 60 + instant.second / 3600
            + instant.microsecond / 3.6e9)
    return swe.julday(instant.year, instant.month, instant.day, hour)


def next_sign_change(sign_at, start, days=90):
    original = sign_at(start)
    previous = start
    for step in range(1, days * 4 + 1):
        candidate = start + timedelta(hours=6 * step)
        if sign_at(candidate) != original:
            while candidate - previous > timedelta(minutes=1):
                midpoint = previous + (candidate - previous) / 2
                if sign_at(midpoint) == original:
                    previous = midpoint
                else:
                    candidate = midpoint
            return sign_at(candidate), candidate
        previous = candidate
    return None


def print_transits(swe, flags, as_of, ascendant, moon, emit):
    emit(f"Slow-planet transits at {as_of.isoformat()} (Lahiri, whole sign):")
    rising_sign = int(ascendant / 30)
    moon_sign = int(moon / 30)
    for name, body, opposite in (
        ("Jupiter", swe.JUPITER, 0), ("Saturn", swe.SATURN, 0),
        ("Rahu", swe.MEAN_NODE, 0), ("Ketu", swe.MEAN_NODE, 180),
    ):
        def sign_at(instant):
            longitude = swe.calc_ut(julian_day(swe, instant), body, flags)[0][0]
            return int((longitude + opposite) % 360 / 30)

        sign = sign_at(as_of)
        emit(f"  {name}: {SIGNS[sign]}, house {(sign - rising_sign) % 12 + 1} "
             f"from Lagna, house {(sign - moon_sign) % 12 + 1} from Moon")
        change = next_sign_change(sign_at, as_of)
        if change:
            next_sign, when = change
            emit(f"    Next sign: {SIGNS[next_sign]} around {when.date()} UTC")


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
    parser.add_argument("--transits", action="store_true",
                        help="Show slow-planet transits and sign changes within 90 days")
    parser.add_argument("--timeline", type=int, metavar="DAYS",
                        help="Show upcoming Vimshottari changes over 1 to 730 days")
    parser.add_argument("--lal-kitab", action="store_true", help="Show house occupancy for a Lal Kitab reading")
    parser.add_argument("--reading", choices=("offline", "ollama", "openai"),
                        help="Add a reading. Without this flag, print the chart only.")
    parser.add_argument("--model", help="Model name for Ollama or OpenAI")
    parser.add_argument("--topic", choices=("overview", "career", "relationships"), default="overview")
    args = parser.parse_args()
    if args.timeline is not None and not 1 <= args.timeline <= 730:
        parser.error("--timeline must be between 1 and 730 days.")
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

    jd = julian_day(swe, birth)
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
    period = print_dasha(birth, moon, as_of, emit, args.timeline) or "outside the available timeline"
    if args.transits:
        try:
            print_transits(swe, flags, as_of, ascendant, moon, emit)
        except (swe.Error, OverflowError) as error:
            parser.exit(1, f"Transit calculation failed: {error}\n")
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
