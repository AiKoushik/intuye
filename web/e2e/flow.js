// End-to-end happy path through every screen of the web test build.
// Needs a fresh backend with LLM_PROVIDER=fake and DEV_LOGIN_ENABLED=true. scripts/e2e.sh starts one and runs this.
// Usage  node web/e2e/flow.js [screenshot-dir]      BASE_URL defaults to http://localhost:8766
const { chromium } = require('playwright');
const S = process.argv[2] || null;
const BASE = process.env.BASE_URL || 'http://localhost:8766';
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1100, height: 920 } });
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  const shot = async (n) => { await p.waitForTimeout(500); if (S) await p.screenshot({ path: `${S}/w-${n}.png` }); };
  await p.goto(BASE + '/');
  await shot('01-welcome');
  await p.click('text=Continue'); await p.click('text=Mexico'); await p.click('text=Continue');
  await p.click('text=Just starting'); await p.fill('input[placeholder="Your name"]', 'Ahsan Iqbal');
  await shot('02-level'); await p.click('button.btn:has-text("Continue")');
  await p.waitForSelector('.field');
  await p.fill('.field', 'me gusta escuchar este en mi mind'); await p.press('.field', 'Enter');
  await p.waitForSelector('.il .g.new');
  await p.fill('.field', 'como te va'); await p.press('.field', 'Enter'); await p.waitForTimeout(400);
  await p.fill('.field', 'I want you to call me tomorrow'); await p.press('.field', 'Enter'); await p.waitForTimeout(500);
  await p.fill('.field', 'when do I use usted?'); await p.press('.field', 'Enter'); await p.waitForSelector('.answer-q');
  await p.click('.g.new'); await shot('03-say');
  // capture simulate
  await p.click('.accessory'); await p.click('text=Send as heard sentences'); await p.waitForSelector('text=/Sent 3 sentences/'); await shot('04-capture');
  await p.click('.sheet .navbtn:has-text("Done")');
  // scenes: new scene with date
  await p.click('.tab:has-text("Scenes")'); await p.waitForTimeout(400);
  await p.click('button[aria-label="Something coming up"]'); await p.fill('input[placeholder^="e.g."]', 'At the dentist');
  await p.fill('textarea[placeholder^="Anything"]', 'my molar has hurt since Monday');
  await p.click('label.row:has-text("It has a date") input'); await shot('05a-new-scene');
  await p.click('.navbtn:has-text("Prepare")'); await p.waitForSelector('.phrase-row');
  await p.waitForSelector('text=Added to the library, anonymously'); await shot('05b-created');
  await p.click('.navbtn.back'); await p.waitForSelector('text=Popular in the library'); await shot('05c-scenes');
  await p.fill('.lib-search input', "going to the dentist's"); await p.waitForSelector('text=In the library'); await shot('05d-search');
  await p.click('.group .row:has-text("At the dentist")'); await p.waitForSelector('text=Use this scene'); await shot('05e-library-scene');
  await p.click('text=Report this scene'); await p.waitForSelector('text=The Spanish is wrong'); await p.click('.sheet .navbtn:has-text("Cancel")');
  await p.click('.navbtn.back'); await p.fill('.lib-search input', ''); await p.waitForSelector('text=Yours');
  await p.click('.row:has-text("At the dentist")'); await p.waitForSelector('.phrase-row'); await p.click('.ready-dots button >> nth=1'); await p.waitForTimeout(400);
  await shot('06-scene');
  await p.click('text=Drill these until they\'re automatic'); await p.waitForSelector('.practice-cue');
  await p.fill('input[placeholder="Or type what you\'d say"]', '¿Puede repetirlo, por favor?'); await p.press('input[placeholder="Or type what you\'d say"]', 'Enter');
  await p.waitForSelector('text=Sounded right'); await shot('06b-drill');
  await p.click('.navbtn.back'); await p.click('text=Shadow these: hear them, say them back'); await p.waitForSelector('.practice-tgt');
  await p.fill('input[placeholder="Or type what you\'d say"]', 'me duele esta'); await p.press('input[placeholder="Or type what you\'d say"]', 'Enter');
  await p.waitForSelector('text=Close. Listen and try again'); await shot('06c-shadow'); await p.click('.navbtn.back');
  await p.click('button.btn:has-text("Rehearse")'); await p.waitForSelector('.bubble.coach');
  await p.fill('input[placeholder="Or type your line"]', 'Me duele esta muela'); await p.press('input[placeholder="Or type your line"]', 'Enter');
  await p.waitForSelector('.bubble.coach >> nth=1');
  await p.fill('input[placeholder="Or type your line"]', 'since yesterday'); await p.press('input[placeholder="Or type your line"]', 'Enter');
  await p.waitForSelector('.native'); await p.click('.bubble.coach >> nth=0'); await shot('07-rehearse');
  await p.click('.navbtn:has-text("End")'); await p.waitForSelector('text=Keep these'); await p.click('.sheet .ready-dots button >> nth=3'); await shot('08-summary');
  await p.click('.sheet .navbtn:has-text("Done")');
  // today + review
  await p.click('.tab:has-text("Today")'); await p.waitForSelector('text=/words ready|Your words/'); await shot('09-today');
  await p.click('button.btn.subtle'); await p.waitForSelector('.rcard'); await shot('10-review-front');
  await p.click('.rcard'); await p.waitForSelector('.ratings:not(.hidden)'); await shot('11-review-back');
  // offline: rate one card with the network off, then come back online and check it synced
  await p.context().setOffline(true); await p.click('.rate.good'); await p.waitForTimeout(300);
  if (await p.evaluate(() => JSON.parse(localStorage.getItem('lc.reviewQueue') || '[]').length) !== 1) throw new Error('offline review not queued');
  await p.context().setOffline(false); await p.waitForSelector('text=/Synced 1 review/');
  if (await p.evaluate(() => JSON.parse(localStorage.getItem('lc.reviewQueue') || '[]').length) !== 0) throw new Error('offline review not synced');
  for (let i = 0; i < 14; i++) { if (!(await p.$('.rcard'))) break; await p.click('.rcard'); await p.waitForSelector('.ratings:not(.hidden)'); await p.click('.rate.good'); await p.waitForTimeout(250); }
  await shot('12-review-done'); await p.click('.cover button.btn:has-text("Done")');
  await p.click('.tab:has-text("Progress")'); await p.waitForSelector('text=Confidence by scene'); await p.waitForSelector('text=Your week');
  await p.waitForSelector('text=Your level, roughly'); await shot('13-progress');
  await p.click('.row:has-text("Wanting someone else")'); await p.waitForSelector('.lesson-opt');
  await p.click('.lesson-opt:has-text("Quiero que me llames.")'); await p.waitForSelector('text=That\'s the one.'); await shot('13a-lesson');
  await p.click('.navbtn.back');
  await p.click('.tab:has-text("Today")'); await p.click('.section-head .link:has-text("See all")'); await p.waitForSelector('.row.moment');
  const before = await p.$$eval('.row.moment', (r) => r.length);
  await p.click('.row.moment >> nth=0 >> button[aria-label^="Delete"]'); await p.waitForSelector('text=Deleted.');
  const after = await p.$$eval('.row.moment', (r) => r.length); if (after !== before - 1) throw new Error('moment not deleted');
  await shot('13b-moments'); await p.click('.navbtn.back');
  await p.click('.tab:has-text("Scenes")'); await p.waitForTimeout(300);
  for (let i = 0; i < 4 && await p.$('.screen:last-child .navbtn.back, .screen .navbtn.back'); i++) { await p.click('.navbtn.back'); await p.waitForTimeout(300); }
  await p.click('.row:has-text("At the dentist") >> nth=0'); await p.waitForSelector('text=I\'m done with this scene');
  await p.click('text=I\'m done with this scene'); await p.waitForSelector('text=Scene moved out of your list');
  await p.click('.tab:has-text("Today")'); await p.click('button[aria-label="Settings"]'); await p.waitForSelector('text=Your Spanish');
  await p.selectOption('select:near(:text("Keep sentences for"))', '30'); await p.waitForTimeout(400);
  await p.fill('input[aria-label="Quiet hours start"]', '21:30'); await p.dispatchEvent('input[aria-label="Quiet hours start"]', 'change'); await p.waitForTimeout(400);
  await p.waitForSelector('text=Coming up'); await shot('14-settings');
  await p.evaluate(() => document.querySelector('.sheet .scroll').scrollTo(0, 600)); await shot('14b-coming-up');
  await p.click('.sheet .navbtn:has-text("Done")');
  await p.click('#theme-toggle'); await p.click('.tab:has-text("Say")'); await shot('15-say-dark');
  const real = errs.filter((e) => e.startsWith('PAGEERROR'));
  console.log('console errors:', JSON.stringify(errs));
  if (real.length) throw new Error('page errors: ' + real.join(' | '));
  console.log('E2E OK');
  await b.close();
})().catch(e => { console.error('E2E FAIL', e.message); process.exit(1); });
