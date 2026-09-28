(function () {
  'use strict';

  const root = document.documentElement;
  const themeToggle = document.querySelector('[data-theme-toggle]');
  let theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  function renderTheme() {
    root.setAttribute('data-theme', theme);
    if (!themeToggle) return;
    themeToggle.innerHTML = theme === 'dark'
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>';
  }
  renderTheme();
  themeToggle && themeToggle.addEventListener('click', function () { theme = theme === 'dark' ? 'light' : 'dark'; renderTheme(); });

  const header = document.getElementById('header');
  window.addEventListener('scroll', function () { header && header.classList.toggle('header--scrolled', window.scrollY > 20); }, { passive: true });

  const navToggle = document.getElementById('navToggle');
  const drawer = document.getElementById('drawer');
  const drawerClose = document.getElementById('drawerClose');
  function setDrawer(open) {
    if (!drawer || !navToggle) return;
    drawer.classList.toggle('open', open);
    navToggle.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  }
  navToggle && navToggle.addEventListener('click', function () { setDrawer(true); });
  drawerClose && drawerClose.addEventListener('click', function () { setDrawer(false); });
  document.querySelectorAll('[data-drawer-link]').forEach(function (link) { link.addEventListener('click', function () { setDrawer(false); }); });

  const form = document.getElementById('contactForm');
  const success = document.getElementById('formSuccess');
  form && form.addEventListener('submit', function (event) {
    event.preventDefault();
    const nameEl = document.getElementById('name');
    const emailEl = document.getElementById('email');
    const messageEl = document.getElementById('message');
    const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    [nameEl, emailEl, messageEl].forEach(function (el) { el.style.borderColor = el.value.trim() ? '' : 'var(--status-warn)'; });
    if (!nameEl.value.trim() || !messageEl.value.trim() || !validEmail.test(emailEl.value.trim())) {
      if (!validEmail.test(emailEl.value.trim())) emailEl.style.borderColor = 'var(--status-warn)';
      return;
    }
    const company = document.getElementById('company').value || '未填寫';
    const service = document.getElementById('service').value || '未指定';
    const budget = document.getElementById('budget').value || '未指定';
    const subject = encodeURIComponent('【AI 工作流需求】' + nameEl.value + '－' + service);
    const body = encodeURIComponent([
      '姓名：' + nameEl.value,
      '電子郵件：' + emailEl.value,
      '職業／公司：' + company,
      '想改善的類型：' + service,
      '預算範圍：' + budget,
      '',
      '目前流程與最耗時的地方：',
      messageEl.value
    ].join('\n'));
    window.location.href = 'mailto:Lucien127@proton.me?subject=' + subject + '&body=' + body;
    form.style.display = 'none';
    success && success.classList.add('show');
    success && success.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  const answers = [
    { keys: ['拿到', '交付', '什麼', '內容'], text: '你會拿到：一套可重用的超級提示詞、Skill 或輕量代理器；繁體中文操作說明書；一小時線上教學。需要知識庫時，也會交付資料格式、搜尋與更新方式。' },
    { keys: ['適合', '對象', '誰'], text: '目前優先服務顧問、講師、律師與法律工作者、小型電商及內容創作者。最適合的是「做法固定、每週重複、耗時但可以清楚驗收」的工作。' },
    { keys: ['費用', '價格', '多少', '報價'], text: '單一工作流包 NT$18,000 起；工作流＋知識庫 NT$38,000 起。資料量或外部系統串接會在動工前書面報價，不會做到一半才追加不明費用。' },
    { keys: ['不做', '邊界', '排除'], text: '目前不承接無限次修改、長期代操、只提供口頭建議，或尚未說清驗收標準的大型客製系統。法律與高風險內容仍須由專業人士確認。' },
    { keys: ['開始', '聯絡', '洽談'], text: '請先說明：你現在怎麼做、每週大約花多久、資料放在哪裡，以及希望得到什麼結果。可使用頁面表單開啟郵件草稿，或加入 LINE：vbn920。' },
    { keys: ['法律', '判決', '法規', '合約'], text: '智研已建立台灣法律資料與判決檢索研究框架，可協助整理、搜尋、保留來源與建立檢查流程；它用來降低遺漏，不替代律師判斷，也不構成法律意見。' },
    { keys: ['知識庫', '文件', '搜尋', '資料'], text: '知識庫方案會先整理資料格式與來源，再建立搜尋、引用與更新方式。目標是讓 AI 回答時能指出依據，而不是只產生看似合理的文字。' }
  ];
  function escapeHtml(value) { return value.replace(/[&<>"']/g, function (char) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]; }); }
  function findAnswer(query) {
    const lower = query.toLowerCase();
    let best = null;
    let score = 0;
    answers.forEach(function (item) {
      const current = item.keys.reduce(function (sum, key) { return sum + (lower.includes(key.toLowerCase()) ? key.length : 0); }, 0);
      if (current > score) { score = current; best = item.text; }
    });
    return best || '這個問題需要看你的實際流程。請在下方留下目前做法、每週花費時間與期望結果，我會先判斷是否適合固定範圍製作。';
  }
  const chatFab = document.getElementById('chatFab');
  const chatPanel = document.getElementById('chatPanel');
  const chatClose = document.getElementById('chatClose');
  const chatBody = document.getElementById('chatBody');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatBadge = document.getElementById('chatBadge');
  let started = false;
  function addMessage(text, who) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg msg--' + who;
    const bubble = document.createElement('div');
    bubble.className = 'msg__bubble';
    bubble.innerHTML = text;
    wrapper.appendChild(bubble);
    chatBody.appendChild(wrapper);
    chatBody.scrollTop = chatBody.scrollHeight;
  }
  function openChat() {
    chatPanel.classList.add('open');
    chatFab.style.display = 'none';
    if (chatBadge) chatBadge.style.display = 'none';
    if (!started) { started = true; addMessage('你好，我可以快速說明交付內容、適合對象、價格與服務邊界。', 'ai'); }
    chatInput && chatInput.focus();
  }
  function closeChat() { chatPanel.classList.remove('open'); chatFab.style.display = 'flex'; }
  chatFab && chatFab.addEventListener('click', openChat);
  chatClose && chatClose.addEventListener('click', closeChat);
  chatForm && chatForm.addEventListener('submit', function (event) {
    event.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;
    addMessage(escapeHtml(query), 'user');
    chatInput.value = '';
    window.setTimeout(function () { addMessage(findAnswer(query), 'ai'); }, 250);
  });
  document.querySelectorAll('#chatQuick button').forEach(function (button) {
    button.addEventListener('click', function () { const query = button.getAttribute('data-q'); addMessage(escapeHtml(query), 'user'); addMessage(findAnswer(query), 'ai'); });
  });

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) { entries.forEach(function (entry) { if (entry.isIntersecting) { entry.target.style.opacity = '1'; entry.target.style.transform = 'translateY(0)'; } }); }, { threshold: 0.1 });
    document.querySelectorAll('.card, .cap, .step, .case, .plan, .stat').forEach(function (el) { el.style.opacity = '0'; el.style.transform = 'translateY(20px)'; el.style.transition = 'opacity .5s ease, transform .5s ease'; observer.observe(el); });
  }
})();
