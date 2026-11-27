// SPDX-License-Identifier: AGPL-3.0-or-later
export const signs = "Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces".split(" ");
const stars = ("Ashwini|Bharani|Krittika|Rohini|Mrigashira|Ardra|Punarvasu|Pushya|Ashlesha|Magha|Purva Phalguni|Uttara Phalguni|Hasta|Chitra|Swati|Vishakha|Anuradha|Jyeshtha|Mula|Purva Ashadha|Uttara Ashadha|Shravana|Dhanishtha|Shatabhisha|Purva Bhadrapada|Uttara Bhadrapada|Revati").split("|");
const lords = "Ketu Venus Sun Moon Mars Rahu Jupiter Saturn Mercury".split(" ");
const years = [7,20,6,10,7,18,16,19,17];
const days = 86400000;
const flag = 65536 | 4;
const bodies = Object.entries({Sun:0, Moon:1, Mars:4, Mercury:2, Jupiter:5, Venus:3, Saturn:6, Rahu:10});
const normalize = angle => (angle % 360 + 360) % 360;
const sign = angle => Math.floor(normalize(angle) / 30);
const navamsha = angle => Math.floor(normalize(angle) * 3 / 10) % 12;
const house = (current, rising) => (current - rising + 12) % 12 + 1;
export const utcDate = ms => new Date(ms).toISOString().slice(0,10);

function cycle(index, start, duration, instant) {
  let weight = 0;
  for (let i = 0; i < 9; i++) {
    const lord = (index + i) % 9;
    const from = start + duration * weight / 120;
    weight += years[lord];
    const end = start + duration * weight / 120;
    if (instant < end) return {lord, from, end};
  }
  throw new Error("The reading date is outside this dasha.");
}

export function dasha(birth, moon, instant) {
  if (instant < birth) return [];
  const segment = moon * 27 / 360;
  const index = Math.floor(segment) % 9;
  const duration = 120 * 365.25 * days;
  const firstStart = birth - (segment % 1) * years[index] * 365.25 * days;
  const start = firstStart + Math.floor((instant - firstStart) / duration) * duration;
  const maha = cycle(index, start, duration, instant);
  const antar = cycle(maha.lord, maha.from, maha.end - maha.from, instant);
  const inner = cycle(antar.lord, antar.from, antar.end - antar.from, instant);
  return [maha, antar, inner].map(period => ({...period, name:lords[period.lord]}));
}

export function birthInstant(date, time, offset, timeZone) {
  const wall = Date.parse(date + "T" + time + ":00Z");
  if (!Number.isFinite(wall)) throw new Error("Check the birth date and time.");
  if (offset) {
    const match = /^([+-])(\d{2}):(\d{2})$/.exec(offset);
    if (!match || +match[2] > 14 || +match[3] > 59 || (+match[2] === 14 && +match[3] > 0)) {
      throw new Error("Enter a valid UTC offset such as +05:30.");
    }
    return Date.parse(date + "T" + time + ":00" + offset);
  }
  const clock = new Intl.DateTimeFormat("en-GB", {
    timeZone, year:"numeric", month:"2-digit", day:"2-digit",
    hour:"2-digit", minute:"2-digit", second:"2-digit", hourCycle:"h23",
  });
  const localEpoch = instant => {
    const parts = Object.fromEntries(clock.formatToParts(instant).map(({type,value}) => [type,value]));
    return Date.parse(parts.year+"-"+parts.month+"-"+parts.day+"T"+parts.hour+":"+parts.minute+":"+parts.second+"Z");
  };
  const probes = [wall - days, wall, wall + days];
  const offsets = new Set(probes.map(instant => localEpoch(instant) - instant));
  const matches = [...offsets].map(delta => wall - delta).filter(instant => localEpoch(instant) === wall);
  if (!matches.length) throw new Error("That local time falls in a clock change. Check the time or enter its UTC offset in Advanced options.");
  if (matches.length > 1) throw new Error("That local time occurred twice. Enter the UTC offset at birth in Advanced options.");
  return matches[0];
}

export function calculate(swe, input) {
  const birth = birthInstant(input.date, input.time, input.offset, input.timeZone);
  const instant = Date.parse(input.reading + "T00:00:00Z");
  if (!Number.isFinite(birth) || !Number.isFinite(instant)) throw new Error("Check the dates and birth time.");
  const jd = swe.dateToJulianDay(new Date(birth));
  const transitJd = swe.dateToJulianDay(new Date(instant));
  swe.setSiderealMode(1);
  const tropical = swe.calculateHouses(jd, +input.lat, +input.lon, "W").ascendant;
  const ascendant = normalize(tropical - swe.getAyanamsaExUt(jd, 4));
  const position = (at, id) => normalize(swe.calculatePosition(at, id, flag).longitude);
  const points = [["Ascendant", ascendant], ...bodies.map(([name,id]) => [name, position(jd,id)])];
  points.push(["Ketu", normalize(points.at(-1)[1] + 180)]);
  const moon = points[2][1];
  const segment = moon * 27 / 360;
  const positions = points.map(([name, angle]) => ({
    name, angle, sign: signs[sign(angle)], house: house(sign(angle),sign(ascendant)),
    d9: signs[navamsha(angle)], d9House: house(navamsha(angle),navamsha(ascendant)),
  }));
  const transits = [["Jupiter",5,0],["Saturn",6,0],["Rahu",10,0],["Ketu",10,180]].map(([name,id,delta]) => {
    const current = sign(position(transitJd,id) + delta);
    return {name, sign:signs[current], house:house(current,sign(ascendant)), moonHouse:house(current,sign(moon))};
  });
  return {positions, transits, star: stars[Math.floor(segment)], pada: Math.floor((segment % 1)*4)+1,
          periods:dasha(birth,moon,instant), birth};
}

export function numerology(birth, year) {
  const [y,m,d] = birth.split("-").map(Number);
  const reduce = n => n ? 1 + (n - 1) % 9 : 0;
  return {"Life Path":reduce(y+m+d), "Birth Day":reduce(d), "Personal Year":reduce(+year+m+d)};
}
