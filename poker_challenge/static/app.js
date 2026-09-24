const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="arena-token"]').content;
let currentResult = null, records = [], handIndex = 0, frameIndex = 0;
function error(message) { $('error').textContent = message; $('error').hidden = false; setTimeout(() => $('error').hidden = true, 9000); }
async function api(path, data) {
  const response = await fetch(path, data ? {method:'POST',headers:{'Content-Type':'application/json','X-Arena-Token':token},body:JSON.stringify(data)} : {});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed');
  return result;
}
function signed(n) { return n > 0 ? '+' + n.toLocaleString() : n.toLocaleString(); }
async function loadBots(selected) {
  const bots = await api('/api/bots');
  const checked = new Set([...document.querySelectorAll('#entrants input:checked')].map(input => input.value));
  const initial = !$('entrants').children.length;
  $('entrants').replaceChildren(...bots.map(bot => {
    const label = document.createElement('label'); label.className = 'trust';
    const input = document.createElement('input'); input.type = 'checkbox'; input.value = bot.id;
    input.checked = initial || checked.has(bot.id) || selected === bot.id;
    input.onchange = tournamentSize;
    label.append(input, document.createTextNode(bot.name)); return label;
  }));
  tournamentSize();
  for (const id of ['bot-a','bot-b']) {
    const previous = $(id).value;
    $(id).replaceChildren(...bots.map(bot => new Option(bot.name + (bot.type === 'uploaded' ? ' · uploaded' : ''), bot.id)));
    $(id).value = selected && id === 'bot-a' ? selected : previous || (id === 'bot-a' ? 'starter' : 'calling_station');
  }
}
async function loadHistory() {
  const matches = await api('/api/matches');
  if (!matches.length) return;
  $('history').replaceChildren(...matches.slice(0,10).map(match => {
    const button = document.createElement('button'); button.className = 'history-item';
    const title = document.createElement('strong'); title.textContent = match.agents.join(' vs ');
    const subtitle = document.createElement('span'); subtitle.textContent = `${match.status} · ${match.hands_completed} hands · ${new Date(match.created_at).toLocaleString()}`;
    button.append(title,subtitle); button.onclick = () => { showResult(match); $('result-title').scrollIntoView({behavior:'smooth',block:'center'}); }; return button;
  }));
}
function showResult(result) {
  currentResult = result; $('empty').hidden = true; $('result').hidden = false; $('replay-panel').hidden = true;
  $('name-a').textContent = result.agents[0]; $('name-b').textContent = result.agents[1];
  $('score-a').textContent = result.net_chips ? signed(result.net_chips[0]) : '—';
  $('score-b').textContent = result.net_chips ? signed(result.net_chips[1]) : '—';
  $('result-title').textContent = result.status === 'forfeit' ? 'Match ended by forfeit' : result.winner === null ? 'An even match.' : `${result.agents[result.winner]} wins.`;
  $('result-note').textContent = result.error || `${result.hands_completed} hands · seed ${result.seed} · Bot A: ${result.bb_per_100[0].toFixed(2)} BB / 100 hands`;
  $('game-rows').replaceChildren(...result.games.map(game => {
    const row = document.createElement('tr');
    [String(game.game).padStart(2,'0'),game.hands,signed(game.net_chips[0]),signed(game.net_chips[1])].forEach(value => { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); }); return row;
  }));
  $('replay-open').disabled = result.hands_completed === 0;
  $('download-result').href = `/api/matches/${result.id}`;
}
$('deals').oninput = () => $('hand-count').textContent = `${Number($('deals').value) * 10} hands total · five games, both seats`;
$('match-form').onsubmit = async event => {
  event.preventDefault(); $('run').disabled = true; $('progress').hidden = false; $('progress').textContent = 'Starting match…';
  try {
    let job = await api('/api/matches', {bot_a:$('bot-a').value,bot_b:$('bot-b').value,paired_deals:Number($('deals').value),seed:Number($('seed').value),trust_scripts:$('trust').checked});
    while (job.status === 'running') {
      $('progress').textContent = `Playing… ${job.hands_completed} / ${job.total_hands} hands. Uploaded bots may take longer.`;
      await new Promise(resolve => setTimeout(resolve,800));
      job = await api(`/api/matches/${job.id}`);
    }
    if (job.status === 'error') throw new Error(job.error);
    showResult(job); await loadHistory(); $('progress').textContent = 'Match saved on this laptop.';
  } catch (exc) { error(exc.message); $('progress').textContent = 'Match could not finish. See the message below.'; }
  finally { $('run').disabled = false; }
};
$('upload-form').onsubmit = async event => {
  event.preventDefault();
  try {
    const file = $('bot-file').files[0];
    if (!file || !file.name.toLowerCase().endsWith('.py') || file.size > 100000) throw new Error('Choose a .py file under 100 KB.');
    const bot = await api('/api/bots', {name:$('bot-name').value, source:await file.text()});
    await loadBots(bot.id); $('upload-status').textContent = `${bot.name} added. Syntax passed; run a short match to validate its decisions.`; $('upload-form').reset();
  } catch (exc) { error(exc.message); }
};
function cards(target, values, placeholders=0) {
  $(target).replaceChildren();
  for (const value of values.concat(Array(Math.max(0,placeholders-values.length)).fill(null))) {
    const card = document.createElement('div'); card.className = 'card';
    if (value) { card.textContent = value[0] + ({c:'♣',d:'♦',h:'♥',s:'♠'}[value[1]]); if ('dh'.includes(value[1])) card.classList.add('red'); }
    else { card.textContent = '·'; card.classList.add('back'); }
    $(target).append(card);
  }
}
function renderHand() {
  const record = records[handIndex], finished = frameIndex === record.frames.length;
  const frame = finished ? {board:record.board,stacks:record.result.final_stacks,pot:0,street:'settled'} : record.frames[frameIndex];
  for (let seat=0;seat<2;seat++) {
    $('seat-'+seat+'-name').textContent = currentResult.agents[record.seat_to_agent[seat]] + (seat === record.button ? ' · BTN' : '');
    cards('cards-'+seat,record.hole_cards[seat]); $('stack-'+seat).textContent = `${frame.stacks[seat]} chips`;
  }
  cards('board',frame.board,5); $('street').textContent = frame.street.toUpperCase(); $('pot').textContent = `Pot ${frame.pot}`;
  const action = record.actions[frameIndex];
  $('decision').textContent = finished ? `${record.result.reason} · seat 0 ${signed(record.result.net_chips[0])}, seat 1 ${signed(record.result.net_chips[1])}` : `Next: ${currentResult.agents[record.seat_to_agent[action.seat]]} ${action.action}${action.amount !== undefined ? ' '+action.amount : ''}`;
  $('step-label').textContent = `${finished ? 'Final result' : 'Before action '+(frameIndex+1)} / ${record.frames.length} actions`;
  $('prev').disabled = frameIndex === 0; $('next').disabled = finished;
}
$('replay-open').onclick = async () => {
  try {
    records = await api(`/api/matches/${currentResult.id}/replays`); handIndex = 0; frameIndex = 0;
    $('hand-picker').replaceChildren(...records.map((r,i) => new Option(`Game ${r.game} · deal ${r.deal} · seat swap ${r.copy+1}`,i)));
    $('replay-panel').hidden = false; renderHand(); $('replay-panel').scrollIntoView({behavior:'smooth',block:'start'});
  } catch (exc) { error(exc.message); }
};
$('hand-picker').onchange = () => { handIndex = Number($('hand-picker').value); frameIndex = 0; renderHand(); };
$('prev').onclick = () => { frameIndex--; renderHand(); };
$('next').onclick = () => { frameIndex++; renderHand(); };
function tournamentSize() {
  const count = document.querySelectorAll('#entrants input:checked').length;
  const matches = count * (count-1) / 2 * Number($('repeats').value);
  $('tournament-size').textContent = `${count} bots · ${matches} matches · up to ${matches * Number($('tournament-deals').value) * 10} hands`;
}
for (const id of ['repeats','tournament-deals']) $(id).oninput = tournamentSize;
function showTournament(result) {
  $('leaderboard').hidden = false;
  const winners = result.standings.filter(row => result.winner_ids.includes(row.id));
  $('leader-title').textContent = !winners.length ? 'No eligible winner' : winners.length > 1 ? 'Tied at the top: ' + winners.map(r => r.name).join(', ') : winners[0].name + ' tops this tournament';
  $('standings').replaceChildren(...result.standings.map(row => {
    const tr = document.createElement('tr');
    [row.rank,row.name,row.points,`${row.wins} / ${row.draws} / ${row.losses}`,signed(row.net_chips),row.eligible ? 'Complete' : `${row.forfeits} forfeits`].forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
    return tr;
  }));
  $('tournament-download').href = `/api/tournaments/${result.id}`;
}
let savedTournaments = [];
async function loadTournaments() {
  savedTournaments = await api('/api/tournaments');
  $('past-tournaments').replaceChildren(new Option('Select a previous tournament',''), ...savedTournaments.map(r => new Option(`${new Date(r.created_at).toLocaleString()} · ${r.standings.length} bots · ${r.total_matches} matches`,r.id)));
}
$('past-tournaments').onchange = () => { const result = savedTournaments.find(r => r.id === $('past-tournaments').value); if(result) showTournament(result); };
$('tournament-form').onsubmit = async event => {
  event.preventDefault(); $('tournament-run').disabled = true; $('run').disabled = true;
  $('tournament-progress').textContent = 'Preparing the schedule…';
  try {
    let job = await api('/api/tournaments', {bot_ids:[...document.querySelectorAll('#entrants input:checked')].map(i => i.value),paired_deals:Number($('tournament-deals').value),seed:Number($('tournament-seed').value),repeats:Number($('repeats').value),trust_scripts:$('tournament-trust').checked});
    while(job.status === 'running') {
      $('tournament-progress').textContent = `${job.matches_completed} / ${job.total_matches} matches complete · ${job.current_pair.join(' vs ')}`;
      await new Promise(resolve => setTimeout(resolve,1000));
      job = await api(`/api/tournaments/${job.id}`);
    }
    if(job.status === 'error') throw new Error(job.error);
    showTournament(job); await loadTournaments();
    $('tournament-progress').textContent = `${job.total_matches} matches finished. Results saved.`;
  } catch(exc) { error(exc.message); $('tournament-progress').textContent = 'Tournament could not finish: '+exc.message; }
  finally { $('tournament-run').disabled = false; $('run').disabled = false; }
};
Promise.all([loadBots(),loadHistory(),loadTournaments()]).catch(exc => error(exc.message));
