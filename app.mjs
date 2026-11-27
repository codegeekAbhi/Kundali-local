// SPDX-License-Identifier: AGPL-3.0-or-later
import {calculate, numerology, utcDate} from './engine.mjs';
const results = document.querySelector('#result');
const picker = document.querySelector('#tool');
const forms = [...document.querySelectorAll('form')];
const paragraph = text => element('p', text);
let engine;

function element(tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}
function table(headers, rows) {
  const wrap = element('div', '');
  wrap.className = 'table-wrap';
  const t = document.createElement('table');
  const head = t.createTHead().insertRow();
  for (const label of headers) head.append(element('th', label));
  const body = t.createTBody();
  for (const row of rows) {
    const tr = body.insertRow();
    for (const value of row) tr.append(element('td', value));
  }
  wrap.append(t);
  return wrap;
}

const themes = [
  'identity and initiative', 'resources and speech', 'communication and effort',
  'home and family', 'creativity and learning', 'routines and obligations',
  'partnerships', 'shared resources and change', 'beliefs and higher learning',
  'career and public responsibilities', 'networks and gains', 'retreat and expenses',
];

const palm = {
  Heart: {straight:'a measured approach to expressing feelings',curved:'an expressive approach to relationships'},
  Head: {straight:'structured thinking',sloping:'imaginative thinking'},
  Life: {'wide-arc':'openness to new settings','close-arc':'comfort with familiar settings'},
  Fate: {clear:'continuity in responsibilities',faint:'changing interests','not-visible':'several possible paths'},
};
for (const [name, shapes] of Object.entries(palm)) {
  const label = element('label', name + ' line');
  const select = document.createElement('select');
  select.name = name;
  select.add(new Option('Unknown', ''));
  for (const shape of Object.keys(shapes)) select.add(new Option(shape.replaceAll('-', ' '), shape));
  label.append(select);
  document.querySelector('#palm-fields').append(label);
}

picker.addEventListener('change', () => {
  for (const form of forms) form.hidden = form.id !== picker.value;
  results.replaceChildren(paragraph('Your results will appear here.'));
});
const today = new Date();
const pad = n => String(n).padStart(2,'0');
document.querySelector('[name=reading]').value =
  today.getFullYear() + '-' + pad(today.getMonth()+1) + '-' + pad(today.getDate());
document.querySelector('[name=year]').value = new Date().getFullYear();

const placeMode = document.querySelector('#place-mode');
const query = document.querySelector('#place-query');
const searchButton = document.querySelector('#search-place');
const matches = document.querySelector('#place-matches');
const matchesLabel = document.querySelector('#place-matches-label');
const placeStatus = document.querySelector('#place-status');
const placeCache = new Map();
let places = [];
let timezoneLookup;

function clearMatches() {
  places = [];
  matches.replaceChildren();
  matchesLabel.hidden = true;
  placeStatus.textContent = '';
}

placeMode.addEventListener('change', () => {
  const manual = placeMode.value === 'coordinates';
  document.querySelector('#place-search').hidden = manual;
  document.querySelector('#place-coordinates').hidden = !manual;
  for (const name of ['lat','lon']) document.querySelector('[name='+name+']').required = manual;
});
query.addEventListener('input', clearMatches);
query.addEventListener('keydown', event => {
  if (event.key === 'Enter') {
    event.preventDefault();
    searchButton.click();
  }
});

searchButton.addEventListener('click', async () => {
  clearMatches();
  const sought = query.value.trim();
  if (sought.length < 2) {
    placeStatus.textContent = 'Enter a place name. Add the district or country to narrow the results.';
    return;
  }
  searchButton.disabled = true;
  placeStatus.textContent = 'Searching…';
  try {
    let found = placeCache.get(sought.toLowerCase());
    if (!found) {
      const url = new URL('https://photon.komoot.io/api/');
      url.search = new URLSearchParams({q:sought,limit:'8',lang:'en'});
      const response = await fetch(url, {credentials:'omit', signal:AbortSignal.timeout(12000)});
      if (!response.ok) throw new Error('Search unavailable');
      const {features} = await response.json();
      found = features.flatMap(({geometry, properties:p}) => {
        const [lon,lat] = geometry?.coordinates ?? [];
        if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) >= 90 || Math.abs(lon) > 180) return [];
        const label = [...new Set([p.name,p.city,p.district,p.county,p.state,p.country].filter(Boolean))].join(', ');
        return label ? [{lat,lon,label}] : [];
      });
      if (placeCache.size >= 40) placeCache.clear();
      placeCache.set(sought.toLowerCase(), found);
    }
    if (query.value.trim() !== sought) return;
    places = found;
    if (!places.length) {
      placeStatus.textContent = 'No matches. Try a nearby town or enter coordinates.';
      return;
    }
    matches.add(new Option('Select a result',''));
    places.forEach(({label},index) => matches.add(new Option(label,String(index))));
    matchesLabel.hidden = false;
    placeStatus.textContent = 'Choose the location that matches your birthplace.';
  } catch {
    if (query.value.trim() === sought) placeStatus.textContent = 'Place search is unavailable. Try again or enter coordinates.';
  } finally {
    searchButton.disabled = false;
  }
});

async function location(data) {
  const search = placeMode.value === 'search';
  const place = search ? (matches.value === '' ? undefined : places[Number(matches.value)])
                       : {lat:Number(data.lat),lon:Number(data.lon)};
  if (!place) throw new Error('Search for your birthplace and choose a matching result, or enter coordinates.');
  const offset = data.offset.trim();
  if (offset) return {...place, offset};
  try {
    timezoneLookup ??= import('https://cdn.jsdelivr.net/npm/tz-lookup@6.1.25/+esm')
      .then(module => module.default).catch(error => { timezoneLookup = undefined; throw error; });
    const lookup = await timezoneLookup;
    return {...place, offset, timeZone:lookup(place.lat,place.lon)};
  } catch {
    throw new Error('Could not infer a birth time zone. Enter your offset in Advanced options.');
  }
}

function loadEngine() {
  if (!engine) {
    engine = import('https://cdn.jsdelivr.net/npm/@swisseph/browser@1.5.0/dist/swisseph-browser.js')
      .then(async ({SwissEphemeris}) => {
        const swe = new SwissEphemeris();
        await swe.init();
        return swe;
      }).catch(() => {
        engine = undefined;
        throw new Error('The chart engine could not load. Check your connection and try again.');
      });
  }
  return engine;
}

async function run(form, data) {
  if (form.id === 'numbers') {
    return [table(['Number','Value'], Object.entries(numerology(data.birth,data.year)))];
  }
  if (form.id === 'palm') {
    const selected = Object.entries(data).filter(([,shape]) => shape);
    if (!selected.length) throw new Error('Choose at least one line.');
    return [
      ...selected.map(([name, shape]) => paragraph(name + ' line: traditionally associated with ' + palm[name][shape] + '.')),
      paragraph('Palmistry cannot reliably predict future events. The life line does not indicate lifespan.'),
    ];
  }

  const selected = await location(data);
  const chart = calculate(await loadEngine(), {...data, ...selected});
  const nodes = [
    paragraph([selected.label, selected.timeZone || ('UTC' + selected.offset)].filter(Boolean).join(' · ')),
    paragraph('Lahiri sidereal zodiac · whole-sign houses · mean lunar nodes'),
    paragraph('Moon nakshatra: ' + chart.star + ', pada ' + chart.pada),
    table(['Point', 'D1 sign', '°', 'House', 'D9 sign', 'D9 house'], chart.positions.map(
      p => [p.name,p.sign,(p.angle % 30).toFixed(3),p.house,p.d9,p.d9House])),
    element('h3', 'Vimshottari dasha'),
  ];
  if (chart.periods.length) {
    nodes.push(table(['Level','Lord','End (UTC)'], chart.periods.map(
      (p,i) => [['Mahadasha','Antardasha','Pratyantardasha'][i],p.name,utcDate(p.end)])));
  } else nodes.push(paragraph('The reading date precedes birth.'));
  nodes.push(
    element('h3', 'Slow-planet transits'),
    table(['Planet','Sign','From ascendant','From Moon'], chart.transits.map(p => [p.name,p.sign,p.house,p.moonHouse])),
    element('h3', 'Traditional reading'),
    paragraph('The natal Moon in house ' + chart.positions[2].house +
       ' emphasizes ' + themes[chart.positions[2].house - 1] +
      '. Transiting Jupiter in house ' + chart.transits[0].house + ' adds a theme of ' +
      themes[chart.transits[0].house - 1] + '. Treat these as traditional themes for reflection.' ),
  );
  return nodes;
}

for (const form of forms) {
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('button');
    button.disabled = true;
    results.replaceChildren(paragraph('Calculating…'));
    try {
      const output = await run(form, Object.fromEntries(new FormData(form)));
      if (picker.value === form.id) results.replaceChildren(...output);
    } catch (error) {
      const notice = paragraph(error.message);
      notice.className = 'error';
      if (picker.value === form.id) results.replaceChildren(notice);
    } finally {
      button.disabled = false;
    }
  });
}
