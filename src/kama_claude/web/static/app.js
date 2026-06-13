const state = {
  sessionId: null,
  busy: false,
  currentAssistant: null,
  sessions: [],
};

const $ = (id) => document.getElementById(id);

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : {'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || 'request failed');
  return data.result;
}

function labelSession() {
  $('sessionLabel').textContent = state.sessionId ? `session ${state.sessionId}` : 'No session';
}

function addMessage(role, text) {
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  el.textContent = text || '';
  $('messages').appendChild(el);
  $('messages').scrollTop = $('messages').scrollHeight;
  return el;
}

function addEvent(name, detail = '', cls = '') {
  const el = document.createElement('div');
  el.className = `event ${cls}`;
  el.innerHTML = `<div class="name"></div><div class="event-meta"></div>`;
  el.querySelector('.name').textContent = name;
  el.querySelector('.event-meta').textContent = detail;
  $('events').prepend(el);
}

async function refreshSessions() {
  const result = await api('/api/sessions');
  state.sessions = result.sessions || [];
  const root = $('sessions');
  root.innerHTML = '';
  for (const s of state.sessions) {
    const item = document.createElement('div');
    item.className = 'session-item' + (s.session_id === state.sessionId ? ' active' : '');
    const name = s.alias ? `@${s.alias}` : s.session_id;
    item.innerHTML = `<div class="session-id"></div><div class="session-meta"></div>`;
    item.querySelector('.session-id').textContent = name;
    item.querySelector('.session-meta').textContent = `${s.status} / ${s.mode} / runs=${s.run_count}`;
    item.onclick = () => resumeSession(s.alias || s.session_id);
    root.appendChild(item);
  }
}

async function createSession() {
  const result = await api('/api/session/create', {mode: 'chat'});
  state.sessionId = result.session_id;
  labelSession();
  $('messages').innerHTML = '';
  addMessage('system', `Created ${state.sessionId}`);
  await refreshSessions();
}

async function resumeSession(id) {
  const result = await api('/api/session/resume', {session_id: id});
  state.sessionId = result.session_id;
  labelSession();
  $('messages').innerHTML = '';
  addMessage('system', `Resumed ${state.sessionId}${result.alias ? ' @' + result.alias : ''}`);
  try {
    const hist = await api(`/api/history?session=${encodeURIComponent(state.sessionId)}`);
    for (const msg of hist.messages || []) renderHistoryMessage(msg);
  } catch (err) {
    addMessage('system', `History unavailable: ${err.message}`);
  }
  await refreshSessions();
}

function renderHistoryMessage(msg) {
  const role = msg.role || 'system';
  const content = msg.content;
  if (typeof content === 'string') {
    addMessage(role === 'assistant' ? 'assistant' : 'user', content);
    return;
  }
  if (Array.isArray(content)) {
    const text = content.map((b) => b.text || b.content || '').filter(Boolean).join('\n');
    if (text) addMessage(role === 'assistant' ? 'assistant' : 'user', text);
  }
}

async function sendMessage(text) {
  if (!state.sessionId) await createSession();
  addMessage('user', text);
  state.busy = true;
  state.currentAssistant = null;
  await api('/api/session/send', {session_id: state.sessionId, content: text});
}

async function cancelRun() {
  if (!state.sessionId) return;
  try {
    await api('/api/session/cancel', {session_id: state.sessionId});
    addEvent('cancel requested', state.sessionId, 'warn');
  } catch (err) {
    addEvent('cancel failed', err.message, 'warn');
  }
}

async function setAlias() {
  const alias = $('aliasInput').value.trim();
  if (!state.sessionId || !alias) return;
  await api('/api/session/alias', {session_id: state.sessionId, alias});
  $('aliasInput').value = '';
  await refreshSessions();
  addEvent('alias set', `@${alias}`, 'ok');
}

async function compact() {
  if (!state.sessionId) return;
  await api('/api/session/compact', {session_id: state.sessionId, focus: ''});
  addEvent('compact requested', state.sessionId, 'ok');
}

function showPermission(event) {
  const box = $('permission');
  const tool = event.tool_name || 'tool';
  const id = event.tool_use_id;
  box.classList.remove('hidden');
  box.innerHTML = `<strong>Permission:</strong> ${tool}<div class="event-meta"></div><div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"></div>`;
  box.querySelector('.event-meta').textContent = event.param_preview || '';
  const actions = box.querySelector('div:last-child');
  const choices = [
    ['allow_once', 'Allow once'],
    ['always_allow', 'Always allow'],
    ['deny_once', 'Deny'],
    ['always_deny', 'Always deny'],
  ];
  for (const [decision, label] of choices) {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.onclick = async () => {
      await api('/api/permission/respond', {tool_use_id: id, decision});
      box.classList.add('hidden');
    };
    actions.appendChild(btn);
  }
}

function handleEvent(event) {
  const type = event.type || '';
  if (type === 'llm.token') {
    if (!state.currentAssistant) state.currentAssistant = addMessage('assistant', '');
    state.currentAssistant.textContent += event.token || '';
    $('messages').scrollTop = $('messages').scrollHeight;
    return;
  }
  if (type === 'session.waiting_for_input') {
    state.busy = false;
    state.currentAssistant = null;
    addEvent(type, event.last_run_id || '', 'ok');
    refreshSessions();
    return;
  }
  if (type === 'permission.requested') {
    showPermission(event);
  }
  if (type === 'tool.call_started') addEvent('tool started', event.tool_name || '');
  else if (type === 'tool.call_finished') addEvent('tool done', event.tool_name || '', 'ok');
  else if (type === 'tool.call_failed') addEvent('tool failed', event.error_message || '', 'warn');
  else if (type.startsWith('run.') || type.startsWith('session.') || type.startsWith('context.')) addEvent(type, event.run_id || event.session_id || '');
}

function connectEvents() {
  const es = new EventSource('/events');
  es.onmessage = (msg) => {
    try { handleEvent(JSON.parse(msg.data)); } catch (err) { console.error(err); }
  };
  es.onerror = () => addEvent('event stream reconnecting', '', 'warn');
}

$('composer').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = $('input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  try { await sendMessage(text); } catch (err) { addMessage('system', `Error: ${err.message}`); }
});
$('input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    $('composer').requestSubmit();
  }
});
$('newSessionBtn').onclick = createSession;
$('refreshBtn').onclick = refreshSessions;
$('cancelBtn').onclick = cancelRun;
$('aliasBtn').onclick = setAlias;
$('compactBtn').onclick = compact;

labelSession();
refreshSessions().catch((err) => addEvent('core unavailable', err.message, 'warn'));
connectEvents();
