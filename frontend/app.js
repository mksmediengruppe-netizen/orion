/**
 * ORION Digital — Frontend v2.0
 * Новый UI: боковая панель, режимы, агенты, стоимость, ask_user
 */

'use strict';

// ══════════════════════════════════════════════════════════════
// STATE
// ══════════════════════════════════════════════════════════════

const STATE = {
  token: null,
  user: null,
  currentChatId: null,
  chats: [],
  messages: [],
  orionMode: 'turbo_standard',
  multiAgent: false,
  isStreaming: false,
  sessionCost: 0,
  maxCost: 2.0,
  attachedFiles: [],
  activeAgents: new Set(),
  abortController: null,
};

const BACKEND = window.location.origin;

// ── Auth helper: всегда добавляет Bearer token ──────────────
function authHeaders(extra = {}) {
  const h = { 'Content-Type': 'application/json', ...extra };
  if (STATE.token) h['Authorization'] = `Bearer ${STATE.token}`;
  return h;
}

async function authFetch(url, opts = {}) {
  if (!opts.headers) opts.headers = {};
  if (STATE.token) opts.headers['Authorization'] = `Bearer ${STATE.token}`;
  opts.credentials = 'include';
  return fetch(url, opts);
}


// ══════════════════════════════════════════════════════════════
// MODE CONFIG
// ══════════════════════════════════════════════════════════════

const MODE_CONFIG = {
  turbo_standard: {
    label: 'Turbo Обычный',
    info: 'DeepSeek везде · Gemini для дизайна',
    maxCost: 2.0,
    model: 'DeepSeek V3.2',
  },
  turbo_premium: {
    label: 'Turbo Премиум',
    info: 'Sonnet для диалога · DeepSeek для работы',
    maxCost: 2.0,
    model: 'Claude Sonnet 4.5',
  },
  pro_standard: {
    label: 'Pro Обычный',
    info: 'Sonnet для оркестрации · DeepSeek для кода',
    maxCost: 10.0,
    model: 'Claude Sonnet 4.5',
  },
  pro_premium: {
    label: 'Pro Премиум',
    info: 'Sonnet везде · Максимальное качество',
    maxCost: 10.0,
    model: 'Claude Sonnet 4.5',
  },
};

const AGENT_CONFIG = {
  designer:   { emoji: '🎨', name: 'Дизайнер',    model: 'Gemini 2.5 Pro' },
  developer:  { emoji: '💻', name: 'Разработчик', model: 'DeepSeek V3.2' },
  devops:     { emoji: '🔧', name: 'DevOps',       model: 'DeepSeek V3.2' },
  analyst:    { emoji: '📊', name: 'Аналитик',     model: 'DeepSeek V3.2' },
  tester:     { emoji: '🧪', name: 'Тестировщик',  model: 'DeepSeek V3.2' },
  integrator: { emoji: '🔌', name: 'Интегратор',   model: 'DeepSeek V3.2' },
};

// ══════════════════════════════════════════════════════════════
// DOM REFS
// ══════════════════════════════════════════════════════════════

const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

const DOM = {
  loginScreen:      $('login-screen'),
  app:              $('app'),
  loginForm:        $('login-form'),
  loginUsername:    $('login-username'),
  loginPassword:    $('login-password'),
  loginError:       $('login-error'),
  loginBtn:         $('login-btn'),

  sidebar:          $('sidebar'),
  sidebarToggle:    $('sidebar-toggle'),
  mobileMenuBtn:    $('mobile-menu-btn'),
  modeGrid:         $('mode-grid'),
  modeInfo:         $('mode-info'),
  agentsList:       $('agents-list'),
  costFill:         $('cost-fill'),
  costCurrent:      $('cost-current'),
  costMax:          $('cost-max'),
  chatsList:        $('chats-list'),
  newChatBtn:       $('new-chat-btn'),
  userAvatar:       $('user-avatar'),
  userName:         $('user-name'),
  userRole:         $('user-role'),
  logoutBtn:        $('logout-btn'),

  chatTitle:        $('chat-title'),
  intentBadge:      $('intent-badge'),
  modelIndicator:   $('model-indicator'),
  modelNameDisplay: $('model-name-display'),
  multiAgentToggle: $('multi-agent-toggle'),
  multiAgentIcon:   $('multi-agent-icon'),
  settingsBtn:      $('settings-btn'),

  messagesArea:     $('messages-area'),
  welcomeScreen:    $('welcome-screen'),
  messagesList:     $('messages-list'),

  askUserModal:     $('ask-user-modal'),
  askUserQuestion:  $('ask-user-question'),
  askUserInput:     $('ask-user-input'),
  askUserSkip:      $('ask-user-skip'),
  askUserSend:      $('ask-user-send'),

  messageInput:     $('message-input'),
  sendBtn:          $('send-btn'),
  stopBtn:          $('stop-btn'),
  attachBtn:        $('attach-btn'),
  fileInput:        $('file-input'),
  charCount:        $('char-count'),
  currentModeLabel: $('current-mode-label'),

  settingsModal:    $('settings-modal'),
  settingsClose:    $('settings-close'),
  settingsCancel:   $('settings-cancel'),
  settingsSave:     $('settings-save'),
  sshHost:          $('ssh-host'),
  sshUser:          $('ssh-user'),
  sshPass:          $('ssh-pass'),
  modesDetail:      $('modes-detail'),
  agentsDetail:     $('agents-detail'),
};

// ══════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  checkAuth();
  createToastContainer();
  // Sprint 3: тема
  const themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
});

function initEventListeners() {
  // Login
  DOM.loginForm.addEventListener('submit', handleLogin);

  // Sidebar
  DOM.sidebarToggle.addEventListener('click', toggleSidebar);
  DOM.mobileMenuBtn.addEventListener('click', toggleMobileSidebar);

  // Mode buttons
  DOM.modeGrid.addEventListener('click', e => {
    const btn = e.target.closest('.mode-btn');
    if (btn) setMode(btn.dataset.mode);
  });

  // Multi-agent toggle
  DOM.multiAgentToggle.addEventListener('click', toggleMultiAgent);

  // New chat
  DOM.newChatBtn.addEventListener('click', createNewChat);

  // Logout
  DOM.logoutBtn.addEventListener('click', handleLogout);

  // Settings
  DOM.settingsBtn.addEventListener('click', openSettings);
  DOM.settingsClose.addEventListener('click', closeSettings);
  DOM.settingsCancel.addEventListener('click', closeSettings);
  DOM.settingsSave.addEventListener('click', saveSettings);
  DOM.settingsModal.addEventListener('click', e => {
    if (e.target === DOM.settingsModal) closeSettings();
  });

  // Message input
  DOM.messageInput.addEventListener('input', handleInputChange);
  DOM.messageInput.addEventListener('keydown', handleInputKeydown);
  DOM.sendBtn.addEventListener('click', sendMessage);
  DOM.stopBtn.addEventListener('click', stopStreaming);

  // File attach
  DOM.attachBtn.addEventListener('click', () => DOM.fileInput.click());
  DOM.fileInput.addEventListener('change', handleFileAttach);

  // Welcome chips
  DOM.welcomeScreen.addEventListener('click', e => {
    const chip = e.target.closest('.chip');
    if (chip) {
      DOM.messageInput.value = chip.dataset.prompt;
      handleInputChange();
      DOM.messageInput.focus();
    }
  });

  // Ask user
  DOM.askUserSend.addEventListener('click', handleAskUserSend);
  DOM.askUserSkip.addEventListener('click', handleAskUserSkip);
  DOM.askUserInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAskUserSend();
    }
  });

  // Mobile: close sidebar on outside click
  document.addEventListener('click', e => {
    if (window.innerWidth <= 768 &&
        DOM.sidebar.classList.contains('mobile-open') &&
        !DOM.sidebar.contains(e.target) &&
        e.target !== DOM.mobileMenuBtn) {
      DOM.sidebar.classList.remove('mobile-open');
    }
  });
}

// ══════════════════════════════════════════════════════════════
// AUTH
// ══════════════════════════════════════════════════════════════

async function checkAuth() {
  try {
    const res = await authFetch(`${BACKEND}/api/auth/me`);
    if (res.ok) {
      const data = await res.json();
      STATE.token = data.token || 'cookie';
      STATE.user = data.user || data;
      showApp();
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const username = DOM.loginUsername.value.trim();
  const password = DOM.loginPassword.value;

  if (!username || !password) return;

  setLoginLoading(true);
  DOM.loginError.classList.add('hidden');

  try {
    const res = await fetch(`${BACKEND}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: username, password }),
    });

    const data = await res.json();

    if (res.ok && data.token) {
      STATE.token = data.token;
      STATE.user = data.user;
      showApp();
    } else {
      showLoginError(data.error || 'Неверный логин или пароль');
    }
  } catch (err) {
    showLoginError('Ошибка подключения к серверу');
  } finally {
    setLoginLoading(false);
  }
}

async function handleLogout() {
  try {
    await authFetch(`${BACKEND}/api/auth/logout`, {
      method: 'POST',
    });
  } catch {}
  STATE.token = null;
  STATE.user = null;
  showLogin();
}

function showLogin() {
  DOM.loginScreen.classList.remove('hidden');
  DOM.app.classList.add('hidden');
  DOM.loginUsername.focus();
}

function showApp() {
  DOM.loginScreen.classList.add('hidden');
  DOM.app.classList.remove('hidden');
  initApp();
}

function setLoginLoading(loading) {
  DOM.loginBtn.disabled = loading;
  DOM.loginBtn.querySelector('.btn-text').textContent = loading ? 'Вход...' : 'Войти';
  DOM.loginBtn.querySelector('.btn-loader').classList.toggle('hidden', !loading);
}

function showLoginError(msg) {
  DOM.loginError.textContent = msg;
  DOM.loginError.classList.remove('hidden');
}

// ══════════════════════════════════════════════════════════════
// APP INIT
// ══════════════════════════════════════════════════════════════

async function initApp() {
  // User info
  if (STATE.user) {
    const name = STATE.user.name || STATE.user.username || 'User';
    DOM.userName.textContent = name;
    DOM.userAvatar.textContent = name[0].toUpperCase();
    DOM.userRole.textContent = STATE.user.role === 'admin' ? 'Administrator' : 'User';
  }

  // Load settings
  await loadSettings();

  // Load chats
  await loadChats();

  // Set mode
  setMode(STATE.orionMode, false);

  // Load modes info
  loadModesInfo();
}

async function loadSettings() {
  try {
    const res = await authFetch(`${BACKEND}/api/settings`);
    if (res.ok) {
      const data = await res.json();
      if (data.ssh_host) DOM.sshHost.value = data.ssh_host;
      if (data.ssh_user) DOM.sshUser.value = data.ssh_user;
      if (data.orion_mode) STATE.orionMode = data.orion_mode;
    }
  } catch {}
}

async function loadModesInfo() {
  try {
    const res = await fetch(`${BACKEND}/api/modes`);
    if (res.ok) {
      const data = await res.json();
      renderModesDetail(data.modes || []);
      renderAgentsDetail(data.models || []);
    }
  } catch {}
}

// ══════════════════════════════════════════════════════════════
// SIDEBAR
// ══════════════════════════════════════════════════════════════

function toggleSidebar() {
  DOM.sidebar.classList.toggle('collapsed');
}

function toggleMobileSidebar() {
  DOM.sidebar.classList.toggle('mobile-open');
}

// ══════════════════════════════════════════════════════════════
// MODE
// ══════════════════════════════════════════════════════════════

function setMode(mode, save = true) {
  STATE.orionMode = mode;
  const cfg = MODE_CONFIG[mode] || MODE_CONFIG.turbo_standard;

  // Update buttons
  $$('.mode-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });

  // Update info
  DOM.modeInfo.textContent = cfg.info;
  DOM.currentModeLabel.textContent = cfg.label;
  DOM.modelNameDisplay.textContent = cfg.model;

  // Update cost max
  STATE.maxCost = cfg.maxCost;
  DOM.costMax.textContent = `/ $${cfg.maxCost.toFixed(2)}`;
  updateCostBar();

  // Update agent models for pro_premium (analyst → Sonnet)
  updateAgentModels(mode);

  if (save) saveSettingsToServer({ orion_mode: mode });
}

function updateAgentModels(mode) {
  const analystModel = (mode === 'pro_premium') ? 'Sonnet 4.5' : 'DeepSeek V3.2';
  const orchestratorModel = (mode.startsWith('pro')) ? 'Sonnet 4.5' : 'DeepSeek V3.2';

  $$('.agent-item').forEach(item => {
    const agent = item.dataset.agent;
    const modelEl = item.querySelector('.agent-model');
    if (!modelEl) return;
    if (agent === 'designer') modelEl.textContent = 'Gemini 2.5';
    else if (agent === 'analyst' && mode === 'pro_premium') modelEl.textContent = 'Sonnet 4.5';
    else modelEl.textContent = 'DeepSeek V3.2';
  });
}

// ══════════════════════════════════════════════════════════════
// MULTI-AGENT
// ══════════════════════════════════════════════════════════════

function toggleMultiAgent() {
  STATE.multiAgent = !STATE.multiAgent;
  DOM.multiAgentIcon.textContent = STATE.multiAgent ? '👥' : '👤';
  DOM.multiAgentToggle.title = STATE.multiAgent ? 'Мульти-агент: ВКЛ' : 'Мульти-агент: ВЫКЛ';
  showToast(STATE.multiAgent ? '👥 Мульти-агент режим включён' : '👤 Одиночный режим', 'info');
}

// ══════════════════════════════════════════════════════════════
// CHATS
// ══════════════════════════════════════════════════════════════

async function loadChats() {
  try {
    const res = await authFetch(`${BACKEND}/api/chats`);
    if (res.ok) {
      const data = await res.json();
      STATE.chats = data.chats || [];
      renderChatsList();
      if (STATE.chats.length > 0) {
        await loadChat(STATE.chats[0].id);
      }
    }
  } catch {}
}

function renderChatsList() {
  DOM.chatsList.innerHTML = '';
  STATE.chats.forEach(chat => {
    const item = document.createElement('div');
    item.className = `chat-item${chat.id === STATE.currentChatId ? ' active' : ''}`;
    item.dataset.chatId = chat.id;
    item.innerHTML = `
      <span class="chat-item-icon">💬</span>
      <span class="chat-item-text">${escHtml(chat.title || 'Новый чат')}</span>
    `;
    item.addEventListener('click', () => loadChat(chat.id));
    DOM.chatsList.appendChild(item);
  });
}

async function loadChat(chatId) {
  try {
    const res = await authFetch(`${BACKEND}/api/chats/${chatId}`);
    if (res.ok) {
      const data = await res.json();
      STATE.currentChatId = chatId;
      STATE.messages = data.messages || [];
      DOM.chatTitle.textContent = data.title || 'Чат';
      renderMessages();
      renderChatsList();
      hideWelcome();
    }
  } catch {}
}

async function createNewChat() {
  try {
    const res = await authFetch(`${BACKEND}/api/chats`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Новый чат' }),
    });
    if (res.ok) {
      const data = await res.json();
      STATE.currentChatId = data.chat_id || data.id;
      STATE.messages = [];
      DOM.chatTitle.textContent = 'Новый чат';
      DOM.messagesList.innerHTML = '';
      showWelcome();
      await loadChats();
    }
  } catch {
    // Fallback: just clear UI
    STATE.currentChatId = null;
    STATE.messages = [];
    DOM.messagesList.innerHTML = '';
    showWelcome();
  }
}

// ══════════════════════════════════════════════════════════════
// MESSAGES
// ══════════════════════════════════════════════════════════════

function renderMessages() {
  DOM.messagesList.innerHTML = '';
  STATE.messages.forEach(msg => {
    if (msg.role === 'user' || msg.role === 'assistant') {
      appendMessage(msg.role, msg.content, msg.agent);
    }
  });
  scrollToBottom();
}

function appendMessage(role, content, agent = null) {
  hideWelcome();

  const msg = document.createElement('div');
  msg.className = `message ${role}`;

  const avatarContent = role === 'user'
    ? (STATE.user?.name?.[0] || 'U').toUpperCase()
    : '🔮';

  const agentBadge = agent
    ? `<span class="msg-agent-badge">${AGENT_CONFIG[agent]?.emoji || '🤖'} ${AGENT_CONFIG[agent]?.name || agent}</span>`
    : '';

  const time = new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });

  msg.innerHTML = `
    <div class="msg-avatar">${avatarContent}</div>
    <div class="msg-content">
      <div class="msg-bubble">${renderMarkdown(content)}</div>
      <div class="msg-meta">
        ${agentBadge}
        <span>${time}</span>
      </div>
    </div>
  `;

  DOM.messagesList.appendChild(msg);
  scrollToBottom();
  return msg;
}

function appendToolEvent(toolName, detail, status = 'running', preview = '') {
  const icons = {
    ssh_execute: '🖥️', file_write: '📝', file_read: '📖',
    browser_navigate: '🌐', browser_get_text: '📄', browser_check_site: '🔍',
    browser_check_api: '🔌', web_search: '🔎', web_fetch: '📡',
    code_interpreter: '🐍', generate_file: '📁', generate_image: '🖼️',
    generate_design: '🎨', create_artifact: '✨', generate_chart: '📊',
    generate_report: '📋', store_memory: '🧠', recall_memory: '💭',
    canvas_create: '📝', task_complete: '✅', read_any_file: '📂',
    analyze_image: '👁️', edit_image: '✏️',
  };

  const icon = icons[toolName] || '⚙️';
  const statusClass = status === 'success' ? 'success' : status === 'error' ? 'error' : 'running';

  const el = document.createElement('div');
  el.className = `tool-event ${statusClass}`;
  el.innerHTML = `
    <div class="tool-event-inner">
      <span class="tool-event-icon">${icon}</span>
      <div style="flex:1;min-width:0">
        <div class="tool-event-name">${toolName}</div>
        ${detail ? `<div class="tool-event-detail">${escHtml(detail.substring(0, 100))}</div>` : ''}
        ${preview ? `<div class="tool-event-preview">${escHtml(preview.substring(0, 200))}</div>` : ''}
      </div>
    </div>
  `;

  DOM.messagesList.appendChild(el);
  scrollToBottom();
  return el;
}

function appendTypingIndicator() {
  const el = document.createElement('div');
  el.className = 'message assistant';
  el.id = 'typing-indicator';
  el.innerHTML = `
    <div class="msg-avatar">🔮</div>
    <div class="msg-content">
      <div class="msg-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>
  `;
  DOM.messagesList.appendChild(el);
  scrollToBottom();
  return el;
}

function removeTypingIndicator() {
  const el = $('typing-indicator');
  if (el) el.remove();
}

// ══════════════════════════════════════════════════════════════
// SEND MESSAGE
// ══════════════════════════════════════════════════════════════

async function sendMessage() {
  const text = DOM.messageInput.value.trim();
  if (!text || STATE.isStreaming) return;

  // Ensure chat exists
  if (!STATE.currentChatId) {
    await createNewChat();
  }

  // Append user message
  appendMessage('user', text);
  STATE.messages.push({ role: 'user', content: text });

  // Clear input
  DOM.messageInput.value = '';
  handleInputChange();

  // Start streaming
  await streamResponse(text);
}

async function streamResponse(userMessage) {
  setStreaming(true);
  resetAgentStatuses();

  const typingEl = appendTypingIndicator();
  let assistantMsgEl = null;
  let assistantBubble = null;
  let fullText = '';
  let currentToolEl = null;

  STATE.abortController = new AbortController();

  try {
    const endpoint = STATE.multiAgent
      ? `${BACKEND}/api/chat/multi-agent`
      : `${BACKEND}/api/chat`;

    const body = {
      message: userMessage,
      chat_id: STATE.currentChatId,
      history: STATE.messages.slice(-10),
      mode: STATE.orionMode,
      multi_agent: STATE.multiAgent,
    };

    // Add file content if attached
    if (STATE.attachedFiles.length > 0) {
      body.file_content = STATE.attachedFiles.map(f => f.content).join('\n\n---\n\n');
      clearAttachments();
    }

    const res = await authFetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal: STATE.abortController.signal,
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw || raw === '[DONE]') continue;

        let event;
        try { event = JSON.parse(raw); } catch { continue; }

        await handleSSEEvent(event, {
          typingEl,
          getAssistantEl: () => assistantMsgEl,
          setAssistantEl: (el, bubble) => { assistantMsgEl = el; assistantBubble = bubble; },
          getFullText: () => fullText,
          setFullText: t => { fullText = t; },
          getCurrentToolEl: () => currentToolEl,
          setCurrentToolEl: el => { currentToolEl = el; },
        });
      }
    }

  } catch (err) {
    if (err.name !== 'AbortError') {
      removeTypingIndicator();
      appendMessage('assistant', `Ошибка: ${err.message}`);
    }
  } finally {
    removeTypingIndicator();
    if (fullText) {
      STATE.messages.push({ role: 'assistant', content: fullText });
      // Remove streaming cursor
      if (assistantBubble) {
        assistantBubble.classList.remove('streaming-cursor');
      }
    }
    setStreaming(false);
    resetAgentStatuses();
  }
}

async function handleSSEEvent(event, ctx) {
  const { type } = event;

  switch (type) {
    case 'intent': {
      // Show intent badge
      const label = event.label || event.data?.intent || '';
      if (label) {
        DOM.intentBadge.textContent = label;
        DOM.intentBadge.classList.remove('hidden');
      }
      // Highlight suggested agents
      const agents = event.data?.suggested_agents || [];
      agents.forEach(a => setAgentStatus(a, 'thinking'));
      break;
    }

    case 'ask_user': {
      // Show ask_user modal
      DOM.askUserQuestion.textContent = event.question || 'Уточните задачу';
      DOM.askUserModal.classList.remove('hidden');
      DOM.askUserInput.focus();
      break;
    }

    case 'text_delta': {
      ctx.typingEl?.remove?.();
      const text = event.text || '';
      ctx.setFullText(ctx.getFullText() + text);

      if (!ctx.getAssistantEl()) {
        const msgEl = document.createElement('div');
        msgEl.className = 'message assistant';
        msgEl.innerHTML = `
          <div class="msg-avatar">🔮</div>
          <div class="msg-content">
            <div class="msg-bubble streaming-cursor"></div>
            <div class="msg-meta"><span>${new Date().toLocaleTimeString('ru', {hour:'2-digit',minute:'2-digit'})}</span></div>
          </div>
        `;
        DOM.messagesList.appendChild(msgEl);
        const bubble = msgEl.querySelector('.msg-bubble');
        ctx.setAssistantEl(msgEl, bubble);
      }

      const bubble = ctx.getAssistantEl()?.querySelector('.msg-bubble');
      if (bubble) {
        bubble.innerHTML = renderMarkdown(ctx.getFullText());
        bubble.classList.add('streaming-cursor');
      }
      scrollToBottom();
      break;
    }

    case 'text_complete': {
      const content = event.content || ctx.getFullText();
      ctx.setFullText(content);
      const bubble = ctx.getAssistantEl()?.querySelector('.msg-bubble');
      if (bubble) {
        bubble.innerHTML = renderMarkdown(content);
        bubble.classList.remove('streaming-cursor');
      }
      DOM.intentBadge.classList.add('hidden');
      break;
    }

    case 'tool_start': {
      const toolEl = appendToolEvent(event.tool, event.args_preview || '', 'running');
      ctx.setCurrentToolEl(toolEl);
      // Set agent active
      const agentMap = {
        ssh_execute: 'devops', file_write: 'developer', file_read: 'developer',
        browser_navigate: 'tester', browser_get_text: 'tester',
        generate_design: 'designer', generate_image: 'designer', create_artifact: 'designer',
        web_search: 'analyst', code_interpreter: 'developer',
      };
      const agent = agentMap[event.tool];
      if (agent) setAgentStatus(agent, 'active');
      break;
    }

    case 'tool_result': {
      const toolEl = ctx.getCurrentToolEl();
      if (toolEl) {
        toolEl.className = `tool-event ${event.success ? 'success' : 'error'}`;
        const preview = toolEl.querySelector('.tool-event-preview');
        if (preview && event.preview) {
          preview.textContent = event.preview.substring(0, 200);
        }
      }
      break;
    }

    case 'tool_calls': {
      // Tool calls batch — show each
      const calls = event.tool_calls || [];
      calls.forEach(call => {
        appendToolEvent(call.function?.name || 'tool', '', 'running');
      });
      break;
    }

    case 'agent_switch': {
      const agent = event.agent;
      if (agent) {
        resetAgentStatuses();
        setAgentStatus(agent, 'active');
        const cfg = AGENT_CONFIG[agent];
        if (cfg) {
          DOM.chatTitle.textContent = `${cfg.emoji} ${cfg.name}`;
        }
      }
      break;
    }

    case 'cost': {
      const cost = event.cost_usd || 0;
      STATE.sessionCost += cost;
      updateCostBar();
      break;
    }

    case 'error': {
      removeTypingIndicator();
      appendMessage('assistant', `❌ ${event.error || 'Произошла ошибка'}`);
      break;
    }

    case 'done':
    case 'complete': {
      DOM.intentBadge.classList.add('hidden');
      break;
    }
  }
}

// ══════════════════════════════════════════════════════════════
// ASK USER
// ══════════════════════════════════════════════════════════════

function handleAskUserSend() {
  const answer = DOM.askUserInput.value.trim();
  if (!answer) return;
  DOM.askUserModal.classList.add('hidden');
  DOM.askUserInput.value = '';
  // Send answer as new message
  DOM.messageInput.value = answer;
  sendMessage();
}

function handleAskUserSkip() {
  DOM.askUserModal.classList.add('hidden');
  DOM.askUserInput.value = '';
}

// ══════════════════════════════════════════════════════════════
// STREAMING CONTROL
// ══════════════════════════════════════════════════════════════

function setStreaming(active) {
  STATE.isStreaming = active;
  DOM.sendBtn.disabled = active;
  DOM.stopBtn.classList.toggle('hidden', !active);
  DOM.messageInput.disabled = active;
}

function stopStreaming() {
  if (STATE.abortController) {
    STATE.abortController.abort();
  }
  setStreaming(false);
  removeTypingIndicator();
  showToast('Остановлено', 'info');
}

// ══════════════════════════════════════════════════════════════
// AGENT STATUS
// ══════════════════════════════════════════════════════════════

function setAgentStatus(agentKey, status) {
  const item = document.querySelector(`.agent-item[data-agent="${agentKey}"]`);
  if (!item) return;
  const dot = item.querySelector('.agent-status');
  if (dot) {
    dot.className = `agent-status ${status}`;
  }
  item.classList.toggle('active', status === 'active' || status === 'thinking');
}

function resetAgentStatuses() {
  $$('.agent-item').forEach(item => {
    item.classList.remove('active');
    const dot = item.querySelector('.agent-status');
    if (dot) dot.className = 'agent-status idle';
  });
}

// ══════════════════════════════════════════════════════════════
// COST BAR
// ══════════════════════════════════════════════════════════════

function updateCostBar() {
  const pct = Math.min(100, (STATE.sessionCost / STATE.maxCost) * 100);
  DOM.costFill.style.width = `${pct}%`;
  DOM.costCurrent.textContent = `$${STATE.sessionCost.toFixed(3)}`;

  DOM.costFill.classList.remove('warning', 'danger');
  if (pct > 80) DOM.costFill.classList.add('danger');
  else if (pct > 60) DOM.costFill.classList.add('warning');
}

// ══════════════════════════════════════════════════════════════
// INPUT
// ══════════════════════════════════════════════════════════════

function handleInputChange() {
  const val = DOM.messageInput.value;
  DOM.sendBtn.disabled = !val.trim() || STATE.isStreaming;

  // Auto-resize
  DOM.messageInput.style.height = 'auto';
  DOM.messageInput.style.height = Math.min(DOM.messageInput.scrollHeight, 200) + 'px';

  // Char count
  if (val.length > 500) {
    DOM.charCount.textContent = val.length;
  } else {
    DOM.charCount.textContent = '';
  }
}

function handleInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!DOM.sendBtn.disabled) sendMessage();
  }
}

// ══════════════════════════════════════════════════════════════
// FILE ATTACH
// ══════════════════════════════════════════════════════════════

function handleFileAttach(e) {
  const files = Array.from(e.target.files);
  files.forEach(file => {
    const reader = new FileReader();
    reader.onload = ev => {
      STATE.attachedFiles.push({
        name: file.name,
        content: ev.target.result,
        size: file.size,
      });
      renderAttachments();
    };
    reader.readAsText(file);
  });
  e.target.value = '';
}

function renderAttachments() {
  let preview = document.querySelector('.attachments-preview');
  if (!preview) {
    preview = document.createElement('div');
    preview.className = 'attachments-preview';
    DOM.messageInput.parentElement.insertBefore(preview, DOM.messageInput);
  }

  preview.innerHTML = STATE.attachedFiles.map((f, i) => `
    <div class="attachment-chip">
      📎 ${escHtml(f.name)}
      <button class="attachment-remove" data-idx="${i}">✕</button>
    </div>
  `).join('');

  preview.querySelectorAll('.attachment-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      STATE.attachedFiles.splice(parseInt(btn.dataset.idx), 1);
      renderAttachments();
    });
  });
}

function clearAttachments() {
  STATE.attachedFiles = [];
  const preview = document.querySelector('.attachments-preview');
  if (preview) preview.remove();
}

// ══════════════════════════════════════════════════════════════
// SETTINGS
// ══════════════════════════════════════════════════════════════

function openSettings() {
  DOM.settingsModal.classList.remove('hidden');
}

function closeSettings() {
  DOM.settingsModal.classList.add('hidden');
}

async function saveSettings() {
  const settings = {
    ssh_host: DOM.sshHost.value.trim(),
    ssh_user: DOM.sshUser.value.trim() || 'root',
    ssh_pass: DOM.sshPass.value,
    orion_mode: STATE.orionMode,
  };

  await saveSettingsToServer(settings);
  closeSettings();
  showToast('Настройки сохранены', 'success');
}

async function saveSettingsToServer(settings) {
  try {
    await authFetch(`${BACKEND}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
  } catch {}
}

function renderModesDetail(modes) {
  if (!DOM.modesDetail) return;
  DOM.modesDetail.innerHTML = modes.map(m => `
    <div class="mode-detail-item${m.key === STATE.orionMode ? ' active' : ''}">
      <div style="flex:1">
        <div class="mode-detail-label">${m.label}</div>
        <div class="mode-detail-desc">${m.description}</div>
      </div>
      <div class="mode-detail-cost">$${m.max_cost_usd}</div>
    </div>
  `).join('');
}

function renderAgentsDetail(models) {
  if (!DOM.agentsDetail) return;
  DOM.agentsDetail.innerHTML = models.map(m => `
    <div class="agent-detail-item">
      <div style="flex:1">
        <div style="font-weight:600;font-size:12px">${m.name}</div>
        <div style="color:var(--text-muted);font-size:11px">${m.description}</div>
      </div>
      <div style="font-size:11px;color:var(--text-muted)">
        in: $${m.input_price}/M · out: $${m.output_price}/M
      </div>
    </div>
  `).join('');
}

// ══════════════════════════════════════════════════════════════
// WELCOME
// ══════════════════════════════════════════════════════════════

function showWelcome() {
  DOM.welcomeScreen.classList.remove('hidden');
  DOM.chatTitle.textContent = 'Новый чат';
  DOM.intentBadge.classList.add('hidden');
}

function hideWelcome() {
  DOM.welcomeScreen.classList.add('hidden');
}

// ══════════════════════════════════════════════════════════════
// SCROLL
// ══════════════════════════════════════════════════════════════

function scrollToBottom() {
  requestAnimationFrame(() => {
    DOM.messagesArea.scrollTop = DOM.messagesArea.scrollHeight;
  });
}

// ══════════════════════════════════════════════════════════════
// MARKDOWN RENDERER (lightweight)
// ══════════════════════════════════════════════════════════════


// ══════════════════════════════════════════════════════════════
// SPRINT 3: ТЕМА (☀/🌙)
// ══════════════════════════════════════════════════════════════

const THEME_KEY = 'orion_theme';

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'dark';
  applyTheme(saved, false);
}

function applyTheme(theme, save = true) {
  document.documentElement.setAttribute('data-theme', theme);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'dark' ? '🌙' : '☀️';

  // Переключаем highlight.js тему
  const darkLink  = document.getElementById('hljs-theme-dark');
  const lightLink = document.getElementById('hljs-theme-light');
  if (darkLink)  darkLink.disabled  = (theme === 'light');
  if (lightLink) lightLink.disabled = (theme === 'dark');

  if (save) localStorage.setItem(THEME_KEY, theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

// Инициализируем тему сразу при загрузке скрипта
initTheme();

// ══════════════════════════════════════════════════════════════
// SPRINT 3: MARKDOWN — marked.js + highlight.js
// ══════════════════════════════════════════════════════════════

// Настраиваем marked.js с highlight.js
function setupMarked() {
  if (typeof marked === 'undefined') return false;

  const renderer = new marked.Renderer();

  // Кастомный рендер блоков кода — с заголовком и кнопкой копирования
  renderer.code = function(code, lang) {
    // В marked.js v9 code может быть объектом
    if (typeof code === 'object' && code !== null) {
      lang = code.lang || '';
      code = code.text || '';
    }
    const langLabel = lang ? lang.toLowerCase() : 'code';
    const highlighted = (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang))
      ? hljs.highlight(code, { language: lang }).value
      : (typeof hljs !== 'undefined' ? hljs.highlightAuto(code).value : escHtml(code));

    const id = 'code-' + Math.random().toString(36).substr(2, 8);
    return `<div class="code-block-wrap">
  <div class="code-block-header">
    <span class="code-lang-label">${escHtml(langLabel)}</span>
    <button class="copy-code-btn" onclick="copyCode('${id}')">📋 Копировать</button>
  </div>
  <pre><code id="${id}" class="hljs language-${escHtml(langLabel)}">${highlighted}</code></pre>
</div>`;
  };

  // Inline code
  renderer.codespan = function(code) {
    if (typeof code === 'object' && code !== null) code = code.text || '';
    return `<code>${escHtml(code)}</code>`;
  };

  marked.setOptions({
    renderer: renderer,
    breaks: true,
    gfm: true,
  });

  return true;
}

// Копирование кода
window.copyCode = function(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const text = el.textContent || el.innerText;
  navigator.clipboard.writeText(text).then(() => {
    // Находим кнопку рядом с этим блоком
    const btn = el.closest('.code-block-wrap')?.querySelector('.copy-code-btn');
    if (btn) {
      btn.textContent = '✅ Скопировано';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = '📋 Копировать';
        btn.classList.remove('copied');
      }, 2000);
    }
  }).catch(() => {
    // Fallback для старых браузеров
    const range = document.createRange();
    range.selectNode(el);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand('copy');
    window.getSelection().removeAllRanges();
  });
};

// ══════════════════════════════════════════════════════════════
// SPRINT 3: renderMarkdown — используем marked.js если доступен
// ══════════════════════════════════════════════════════════════

function renderMarkdown(text) {
  if (!text) return '';

  // Используем marked.js если загружен
  if (typeof marked !== 'undefined') {
    // Инициализируем при первом вызове
    if (!window._markedSetup) {
      window._markedSetup = setupMarked();
    }
    try {
      const html = marked.parse(text);
      return html;
    } catch (e) {
      console.warn('marked.js error, fallback:', e);
    }
  }

  // Fallback: собственный рендерер
  return renderMarkdownFallback(text);
}

function renderMarkdownFallback(text) {
  if (!text) return '';

  let html = escHtml(text);

  // Code blocks с кнопкой копирования
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const id = 'code-' + Math.random().toString(36).substr(2, 8);
    const langLabel = lang || 'code';
    return `<div class="code-block-wrap">
  <div class="code-block-header">
    <span class="code-lang-label">${langLabel}</span>
    <button class="copy-code-btn" onclick="copyCode('${id}')">📋 Копировать</button>
  </div>
  <pre><code id="${id}" class="lang-${langLabel}">${code.trim()}</code></pre>
</div>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold & Italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // HR
  html = html.replace(/^---$/gm, '<hr>');

  // Unordered lists
  html = html.replace(/^[\*\-] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`);

  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // Tables
  html = html.replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)+)/g, (_, header, rows) => {
    const ths = header.split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
    const trs = rows.trim().split('\n').map(row => {
      const tds = row.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
  });

  // Paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = `<p>${html}</p>`;
  html = html.replace(/\n/g, '<br>');

  // Cleanup
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<h[1-6]>)/g, '$1');
  html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<pre>)/g, '$1');
  html = html.replace(/(<\/pre>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)<\/p>/g, '$1');
  html = html.replace(/<p>(<table>)/g, '$1');
  html = html.replace(/(<\/table>)<\/p>/g, '$1');
  html = html.replace(/<p>(<hr>)<\/p>/g, '$1');
  html = html.replace(/<p>(<blockquote>)/g, '$1');
  html = html.replace(/(<\/blockquote>)<\/p>/g, '$1');

  return html;
}

// ══════════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════════

function createToastContainer() {
  if (document.getElementById('toast-container')) return;
  const container = document.createElement('div');
  container.className = 'toast-container';
  container.id = 'toast-container';
  document.body.appendChild(container);
}

function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = '0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ══════════════════════════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════════════════════════

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ══════════════════════════════════════════════════════════════
// THEME TOGGLE (Блок 2 — Sprint 3)
// ══════════════════════════════════════════════════════════════
(function initTheme() {
  var btn = document.getElementById('theme-toggle');
  var html = document.documentElement;
  var darkCss  = document.getElementById('hljs-theme-dark');
  var lightCss = document.getElementById('hljs-theme-light');

  function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    if (theme === 'light') {
      if (darkCss)  darkCss.disabled  = true;
      if (lightCss) lightCss.disabled = false;
      if (btn) btn.textContent = '\u2600';
    } else {
      if (darkCss)  darkCss.disabled  = false;
      if (lightCss) lightCss.disabled = true;
      if (btn) btn.textContent = '\uD83C\uDF19';
    }
    localStorage.setItem('orion-theme', theme);
  }

  var saved = localStorage.getItem('orion-theme') || 'dark';
  applyTheme(saved);

  if (btn) {
    btn.addEventListener('click', function() {
      var current = html.getAttribute('data-theme') || 'dark';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }
})();

// ══════════════════════════════════════════════════════════════
// MARKDOWN RENDER + CODE COPY (Блок 3 — Sprint 3)
// ══════════════════════════════════════════════════════════════
(function initMarkdown() {
  if (typeof marked === 'undefined') return;

  marked.setOptions({
    breaks: true,
    gfm: true
  });

  window.renderMarkdown = function(text) {
    if (!text) return '';
    try {
      return marked.parse(text);
    } catch(e) {
      return text;
    }
  };

  window.addCopyButtons = function(container) {
    if (!container) return;
    container.querySelectorAll('pre code').forEach(function(block) {
      if (block.parentElement.querySelector('.copy-btn')) return;
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'Копировать';
      btn.addEventListener('click', function() {
        navigator.clipboard.writeText(block.textContent).then(function() {
          btn.textContent = '\u2713 Скопировано';
          setTimeout(function() { btn.textContent = 'Копировать'; }, 2000);
        });
      });
      block.parentElement.style.position = 'relative';
      block.parentElement.appendChild(btn);
    });
    if (typeof hljs !== 'undefined') {
      container.querySelectorAll('pre code:not(.hljs)').forEach(function(b) {
        hljs.highlightElement(b);
      });
    }
  };
})();

// ══════════════════════════════════════════════════════════════
// AUTO-HEIGHT TEXTAREA (Блок 3 — Sprint 3)
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', function() {
  var ta = document.getElementById('msgInput');
  if (!ta) return;
  function autoResize() {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
  }
  ta.addEventListener('input', autoResize);
  autoResize();
});
