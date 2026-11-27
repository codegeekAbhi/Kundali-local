// SPDX-License-Identifier: AGPL-3.0-or-later
import {utcDate} from './engine.mjs';

const themes = [
  ['identity and initiative','balancing your own priorities with others’ expectations','choose one decision you can make this week'],
  ['resources and communication','pressure around costs or sensitive conversations','write down your priorities before making commitments'],
  ['communication and effort','scattered outreach or inconsistent follow-through','set a small weekly target and track replies'],
  ['home and family','competing demands at home','agree on who owns each recurring responsibility'],
  ['creativity and learning','starting more projects than you finish','finish one piece of work you can show others'],
  ['routines and workload','a backlog or competing daily obligations','set a repeatable schedule and clear its biggest bottleneck'],
  ['partnerships','unclear expectations between people','ask directly what each person expects and can commit to'],
  ['shared resources and change','uncertainty around joint responsibilities','clarify who owns each decision and what information is missing'],
  ['learning and direction','uncertainty about which direction to pursue','try one bounded experiment before committing'],
  ['career and responsibility','pressure to demonstrate results or choose a direction','prepare concrete examples of the outcomes you delivered'],
  ['networks and goals','too many leads with little follow-through','reconnect with a few people who know your work'],
  ['expenses and downtime','overcommitment or a lack of time to recover','review recurring commitments and protect time to reset'],
];

const meanings = [
  ['Initiative','Choose one thing you can start independently.'],
  ['Cooperation','Ask where clearer communication or support would help.'],
  ['Expression','Give an idea a concrete form through writing, speaking, or making.'],
  ['Structure','Make one important routine easier to repeat.'],
  ['Adaptability','Try a small change before making a larger commitment.'],
  ['Care and responsibility','Balance a commitment to someone else with time for yourself.'],
  ['Reflection','Make room to study a question before acting on it.'],
  ['Organization and ambition','Define a measurable goal and review how you use your resources.'],
  ['Completion and service','Finish one lingering task or decide what you can let go.'],
];

export function numerologyReading(numbers) {
  const lenses = {
    'Life Path':'A broad theme for how you approach choices and long-term goals.',
    'Birth Day':'A theme for strengths you might draw on in everyday situations.',
    'Personal Year':'A theme to reflect on in the selected calendar year.',
  };
  return Object.entries(numbers).map(([label,number]) => {
    const [theme,reflection] = meanings[number-1];
    return [label,number,theme,lenses[label]+' '+reflection];
  });
}

export function vedicReading(chart, focus) {
  const saturn = chart.transits.find(p=>p.name==='Saturn');
  const jupiter = chart.transits.find(p=>p.name==='Jupiter');
  const [pressure, challenge, response] = themes[saturn.house-1];
  const [support,,supportAction] = themes[jupiter.house-1];
  let advice = 'To work with the Jupiter theme, '+supportAction+'.';
  if (focus === 'career') {
    advice = jupiter.house === 11
      ? 'Ask former colleagues for introductions, then follow up on active interview leads.'
      : 'Choose a few well-matched openings and prepare examples of what you delivered.';
  } else if (focus === 'relationships') {
    advice = 'Use the Jupiter theme of '+support+' as a prompt for a direct conversation about what each person needs.';
  }
  const timing = chart.changes.map(change => change.name
    ? utcDate(change.date)+' UTC — '+change.name+' enters '+change.sign
      +' (house '+change.house+'), shifting the traditional emphasis toward '+themes[change.house-1][0]+'.'
    : utcDate(change.date)+' UTC — Vimshottari changes to '+change.sequence+'.');
  return {
    challenge:'Saturn in house '+saturn.house+' puts '+pressure+' in focus. You might notice '+challenge+'.',
    response:'A practical response is to '+response+'. Jupiter in house '+jupiter.house+
      ' highlights '+support+'. '+advice,
    period:chart.periods.length ? 'Current Vimshottari: '+chart.periods.map(p=>p.name).join(' / ')+'.' : '',
    timing,
  };
}
