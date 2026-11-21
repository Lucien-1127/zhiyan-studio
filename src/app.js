'use strict';

const root = document.documentElement;
const themeButton = document.querySelector('#theme');
const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
let preference;
try {
  preference = localStorage.getItem('zhiyan-theme');
} catch { /* Some browsers block storage for local files. */ }
function renderTheme() {
  const dark = preference === 'dark' || (preference !== 'light' && systemTheme.matches);
  root.dataset.theme = dark ? 'dark' : 'light';
  themeButton.setAttribute('aria-label', dark ? '切換為淺色模式' : '切換為深色模式');
  themeButton.title = themeButton.getAttribute('aria-label');
  document.querySelector('meta[name="theme-color"]').content = getComputedStyle(root).getPropertyValue('--paper').trim();
}
renderTheme();
themeButton.hidden = false;
systemTheme.addEventListener('change', renderTheme);
themeButton.addEventListener('click', () => {
  preference = root.dataset.theme === 'light' ? 'dark' : 'light';
  renderTheme();
  try { localStorage.setItem('zhiyan-theme', preference); } catch { /* Session choice still applies. */ }
});

const menu = document.querySelector('#menu');
const menuToggle = menu.querySelector('summary');
function closeMenu(restoreFocus) {
  if (!menu.open) return;
  menu.open = false;
  if (restoreFocus) menuToggle.focus();
}
menu.querySelector('nav').addEventListener('click', event => {
  const link = event.target.closest('a');
  if (!link) return;
  closeMenu(false);
  const heading = document.querySelector(link.hash + ' h2');
  if (heading) {
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menu.open) closeMenu(true);
});
document.addEventListener('click', event => {
  if (!menu.contains(event.target)) closeMenu(false);
});
document.addEventListener('focusin', event => {
  if (!menu.contains(event.target)) closeMenu(false);
});
window.matchMedia('(min-width: 54.01rem)').addEventListener('change', event => {
  if (event.matches) closeMenu(false);
});

const contactForm = document.querySelector('#contactForm');
const contactMailto = document.querySelector('#contact-email').getAttribute('href');
const contactEmail = contactMailto.slice('mailto:'.length);
const plan = document.querySelector('#plan');
const draftResult = document.querySelector('#draftResult');
const draftText = document.querySelector('#draftText');
const copyStatus = document.querySelector('#copyStatus');
const openDraft = document.querySelector('#openDraft');
openDraft.href = contactMailto;
document.querySelector('#draftRecipient').textContent = contactEmail;
contactForm.hidden = false;
function discardDraft() {
  draftResult.hidden = true;
  draftText.value = '';
  openDraft.href = contactMailto;
  copyStatus.textContent = '';
}
document.querySelectorAll('[data-plan], [data-service]').forEach(link => {
  link.addEventListener('click', () => {
    if (link.dataset.plan) plan.value = link.dataset.plan;
    if (link.dataset.service) contactForm.elements.service.value = link.dataset.service;
    discardDraft();
  });
});
contactForm.addEventListener('input', event => {
  event.target.setCustomValidity?.('');
  discardDraft();
});
contactForm.addEventListener('change', discardDraft);
contactForm.addEventListener('submit', event => {
  event.preventDefault();
  for (const field of [contactForm.elements.name, contactForm.elements.message]) {
    if (!field.value.trim()) {
      field.setCustomValidity('請填寫這個欄位。');
      field.reportValidity();
      return;
    }
  }
  const data = new FormData(contactForm);
  const read = name => String(data.get(name) || '').trim();
  const subject = '【智研工作流需求】' + read('name') + '－' + read('plan');
  const body = [
    '稱呼：' + read('name'), '電子郵件：' + read('email'),
    '想了解的方案：' + read('plan'), '職業／公司：' + (read('company') || '未填寫'),
    '工作類型：' + (read('service') || '未指定'), '預算範圍：' + (read('budget') || '尚未確定'),
    '', '目前流程與最耗時的地方：', read('message')
  ].join('\r\n');
  draftText.value = '主旨：' + subject + '\r\n\r\n' + body;
  draftResult.hidden = false;
  draftResult.scrollIntoView({ block: 'nearest' });
  openDraft.href = contactMailto + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
  draftText.focus({ preventScroll: true });
});
document.querySelector('#copyDraft').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(draftText.value);
    copyStatus.textContent = '已複製草稿。';
  } catch {
    draftText.focus();
    draftText.select();
    copyStatus.textContent = '已選取草稿，可使用裝置的複製功能。';
  }
});

const answers = [
  { keys: ['交付', '拿到', '手冊', '教學'], text: '每案包含可重用工作流、繁體中文操作手冊與一小時教學。交付後有 14 天約定範圍內的瑕疵修正。' },
  { keys: ['對象', '適合', '誰'], text: '顧問、講師、法律工作者、電商、創作者與小型團隊都可以從一項固定、經常重複、有明確輸出的工作開始。' },
  { keys: ['費用', '價格', '多少錢', '預算', '報價', '用量', '訂閱', '一次性'], text: '一次性建置費為單一工作流包 NT$18,000 起，工作流＋知識庫 NT$38,000 起。額外系統整合另行報價。若需第三方訂閱或用量費用，會在動工前另列。' },
  { keys: ['邊界', '不做', '代操', '修改', '排除'], text: '固定範圍方案涵蓋約定工具、手冊與教學。長期代操、無限次修改及單純口頭顧問服務都在範圍外。' },
  { keys: ['開始', '聯絡', '洽談', 'line', '信箱', '郵件', 'email', 'gmail'], text: '可寄信到 ' + contactEmail + '、用洽談表單準備草稿，或加 LINE（vbn920）。請說明目前做法與期望結果。' },
  { keys: ['prompt factory', '提示詞', '等義壓縮'], text: '提示詞工廠可從需求設計指令，也能審查現有版本。等義壓縮會保留任務、限制與輸出格式，再用範例核對結果。' },
  { keys: ['writer compiler', '寫作指令', '寫作', '文風'], text: 'Writer Compiler 可依現成條件快速整理指令，或透過引導訪談釐清讀者與文風，產出可重用的寫作指令。可在工作類型選「寫作指令」詢問示範。' },
  { keys: ['skill.md', '客製技能', '技能檔'], text: '可把團隊的操作方法寫成客製 SKILL.md，列明輸入、步驟與驗收範例，再用手冊和實作教學交接。' },
  { keys: ['短影音', 'cineagent', 'ffmpeg', '背景鎖定'], text: '短影音依序進行題材蒐集、腳本、視覺生成、圖生影、語音合成與自動剪輯。需要固定背景時，先選定參考畫面，再逐片驗收背景鎖定效果。' },
  { keys: ['法律', '合約', '法規', '判決'], text: '可協助整理與查找法律資料，保留引用供核對。重要結果仍需由合格專業人士確認。' },
  { keys: ['知識庫', '搜尋', '文件', '資料'], text: '工作流＋知識庫方案會約定資料格式、搜尋與來源引用，並交付日後更新的操作方法。' }
];
function findAnswer(question) {
  const query = question.toLowerCase();
  let bestScore = 0;
  let reply = '這個問題需要了解實際工作。請在洽談需求表單說明，或直接寄信到 ' + contactEmail + '。';
  for (const answer of answers) {
    const score = answer.keys.reduce((sum, key) => sum + (query.includes(key) ? key.length : 0), 0);
    if (score > bestScore) {
      bestScore = score;
      reply = answer.text;
    }
  }
  return reply;
}
const chat = document.querySelector('#chat');
const chatOpen = document.querySelector('#chatOpen');
const chatLog = document.querySelector('#chatLog');
const chatInput = document.querySelector('#chatInput');
function replyTo(question) {
  const query = question.trim();
  if (!query) return;
  const userMessage = document.createElement('p');
  userMessage.className = 'question';
  userMessage.textContent = query;
  const answer = document.createElement('p');
  answer.textContent = findAnswer(query);
  chatLog.append(userMessage, answer);
  chatLog.scrollTop = chatLog.scrollHeight;
}
if (typeof chat.showModal === 'function') {
  chatOpen.hidden = false;
  chatOpen.addEventListener('click', () => chat.showModal());
  chat.addEventListener('close', () => chatOpen.focus());
  chat.querySelector('.quick').addEventListener('click', event => {
    if (event.target.matches('button')) replyTo(event.target.textContent);
  });
  document.querySelector('#chatForm').addEventListener('submit', event => {
    event.preventDefault();
    replyTo(chatInput.value);
    chatInput.value = '';
    chatInput.focus();
  });
}
