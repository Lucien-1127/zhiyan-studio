/* app.js — 智研接案服務銷售頁互動 + AI 客服知識庫
   客服以關鍵字知識庫驅動，無需 API 金鑰，可直接於靜態託管與自有網域運作。
   知識內容源自儲存庫實際素材，不暴露任何儲存庫網址。 */

(function () {
  'use strict';

  /* ============ 主題切換 ============ */
  const themeToggle = document.querySelector('[data-theme-toggle]');
  const root = document.documentElement;
  let theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  root.setAttribute('data-theme', theme);

  function setThemeIcon() {
    if (!themeToggle) return;
    themeToggle.innerHTML = theme === 'dark'
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    themeToggle.setAttribute('aria-label', theme === 'dark' ? '切換至淺色模式' : '切換至深色模式');
  }
  setThemeIcon();

  themeToggle && themeToggle.addEventListener('click', function () {
    theme = theme === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', theme);
    setThemeIcon();
  });

  /* ============ Header 滾動行為 ============ */
  const header = document.getElementById('header');
  let lastScroll = 0;
  window.addEventListener('scroll', function () {
    const y = window.scrollY;
    if (y > 20) header.classList.add('header--scrolled');
    else header.classList.remove('header--scrolled');
    lastScroll = y;
  }, { passive: true });

  /* ============ 行動版選單 ============ */
  const navToggle = document.getElementById('navToggle');
  const drawer = document.getElementById('drawer');
  const drawerClose = document.getElementById('drawerClose');

  function openDrawer() { drawer.classList.add('open'); navToggle.setAttribute('aria-expanded', 'true'); document.body.style.overflow = 'hidden'; }
  function closeDrawer() { drawer.classList.remove('open'); navToggle.setAttribute('aria-expanded', 'false'); document.body.style.overflow = ''; }

  navToggle && navToggle.addEventListener('click', openDrawer);
  drawerClose && drawerClose.addEventListener('click', closeDrawer);
  document.querySelectorAll('[data-drawer-link]').forEach(function (a) {
    a.addEventListener('click', closeDrawer);
  });

  /* ============ 表單處理 ============ */
  const form = document.getElementById('contactForm');
  const success = document.getElementById('formSuccess');

  form && form.addEventListener('submit', function (e) {
    e.preventDefault();
    const required = ['name', 'email', 'message'];
    let valid = true;
    required.forEach(function (id) {
      const el = document.getElementById(id);
      if (!el.value.trim()) { el.style.borderColor = 'var(--status-warn)'; valid = false; }
      else el.style.borderColor = '';
    });
    const email = document.getElementById('email');
    if (email.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
      email.style.borderColor = 'var(--status-warn)'; valid = false;
    }
    if (!valid) return;

    const name = encodeURIComponent(document.getElementById('name').value);
    const mail = encodeURIComponent(document.getElementById('email').value);
    const company = encodeURIComponent(document.getElementById('company').value || '未填寫');
    const service = encodeURIComponent(document.getElementById('service').value || '未指定');
    const budget = encodeURIComponent(document.getElementById('budget').value || '未指定');
    const msg = encodeURIComponent(document.getElementById('message').value);
    const subject = encodeURIComponent('【接案洽談】' + document.getElementById('name').value + ' — ' + (document.getElementById('service').value || '需求諮詢'));
    const body = encodeURIComponent(
      '姓名：' + decodeURIComponent(name) + '\n' +
      '電子郵件：' + decodeURIComponent(mail) + '\n' +
      '公司/組織：' + decodeURIComponent(company) + '\n' +
      '需求類型：' + decodeURIComponent(service) + '\n' +
      '預算範圍：' + decodeURIComponent(budget) + '\n\n' +
      '需求描述：\n' + decodeURIComponent(msg)
    );
    const mailtoLink = 'mailto:Lucien127@proton.me?subject=' + subject + '&body=' + body;

    // 開啟郵件草稿
    window.location.href = mailtoLink;

    form.style.display = 'none';
    success.classList.add('show');
    // 更新成功訊息文案
    const successH = success.querySelector('h3');
    const successP = success.querySelector('p');
    if (successH) successH.textContent = '已為您產生郵件草稿';
    if (successP) successP.innerHTML = '我們已開啟您的郵件軟體並填妥內容，請確認後寄出。若未自動開啟，請直接來信至 <a href="mailto:Lucien127@proton.me" style="color:var(--gold-strong);">Lucien127@proton.me</a>。我們會在 1 個工作天內回覆。';
    success.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  /* ============ AI 客服 ============ */
  const chatFab = document.getElementById('chatFab');
  const chatPanel = document.getElementById('chatPanel');
  const chatClose = document.getElementById('chatClose');
  const chatBody = document.getElementById('chatBody');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatBadge = document.getElementById('chatBadge');
  let chatStarted = false;

  function nowTime() {
    const d = new Date();
    return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0');
  }

  function addMsg(text, who) {
    const wrap = document.createElement('div');
    wrap.className = 'msg msg--' + who;
    const bubble = document.createElement('div');
    bubble.className = 'msg__bubble';
    bubble.innerHTML = text;
    const time = document.createElement('div');
    time.className = 'msg__time';
    time.textContent = nowTime();
    wrap.appendChild(bubble);
    wrap.appendChild(time);
    chatBody.appendChild(wrap);
    chatBody.scrollTop = chatBody.scrollHeight;
    return bubble;
  }

  function addTyping() {
    const t = document.createElement('div');
    t.className = 'typing';
    t.id = 'typingIndicator';
    t.innerHTML = '<span></span><span></span><span></span>';
    chatBody.appendChild(t);
    chatBody.scrollTop = chatBody.scrollHeight;
  }
  function removeTyping() {
    const t = document.getElementById('typingIndicator');
    if (t) t.remove();
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* 知識庫 —— 關鍵字比對，內容源自儲存庫實際素材 */
  const KB = [
    { keys: ['服務', '提供', '能做', '做什麼', '有哪些', '項目', '接什麼'],
      answer: '智研提供六大類 AI 接案服務：<br><br>一、<b>法律 AI 系統開發</b> — 書狀初稿審查、條文速查、判決分析，附帶可驗證來源<br>二、<b>RAG 檢索增強系統</b> — 為內部知識庫打造智慧搜尋與精準問答<br>三、<b>多模型 Agent 架構</b> — 多技能、多模型編排與全息記憶<br>四、<b>提示詞工程與優化</b> — 系統化設計、壓力檢核與跨模型適配<br>五、<b>API 整合與路由</b> — 串接各大 LLM、額度防護與監控<br>六、<b>企業 AI 諮詢顧問</b> — 從研究、架構到部署的完整諮詢<br><br>請問您對哪一項最感興趣？' },
    { keys: ['法律', 'legal', '法條', '判決', '書狀', '律師', '法規'],
      answer: '法律 AI 是我們的核心專長。智研打造了一套以台灣法規為核心的 AI 研究框架，特色是：<br><br>• <b>強制引用政策</b>：AI 列出來源後，會回頭驗證那個來源是否存在、說的是否同一件事，杜絕捏造法條<br>• <b>安全路由</b>：當使用者情緒激動或帶創傷訊號，系統會在法律分析前先介入接住使用者<br>• <b>事實閘門</b>：資訊不足時標示「待查」或「推論」，而非硬擠自信的錯誤答案<br>• <b>47,001 條法規</b>本地 RAG 資料庫，支援全文檢索與語意搜尋<br><br>應用層包含法律諮詢、合約自動產生、法規異動監控、智慧搜尋等六大模組。想了解如何套用至您的場景嗎？' },
    {
      keys: ['rag', '檢索', '搜尋', '向量', 'embedding', '知識庫', '問答'],
      answer: 'RAG（檢索增強生成）是我們的強項。我們能為您的內部文件、法規、判決書或企業資料打造智慧問答系統：<br><br>• <b>SQLite FTS5</b> 全文檢索 + <b>向量語意搜尋</b>雙引擎<br>• 支援 BGE-M3、text-embedding-3-large 等嵌入模型<br>• 多源資料彙整查詢<br>• 答案附帶來源可追蹤、可驗證<br><br>我們已實際建置含 47,001 條法規的 RAG 系統。歡迎至<a href="#contact">洽談表單</a>說明您的資料類型與需求。'
    },
    {
      keys: ['agent', '代理', '多模型', '路由', 'hermes', '自動化', '工作流'],
      answer: '我們建構多模型 Agent 架構系統，包含：<br><br>• <b>多技能架構</b>：113 項技能、27 類分類的技能庫<br>• <b>模型路由</b>：依任務自動分派至最適模型（DeepSeek、Claude、Gemini 等）<br>• <b>額度防護</b>：在多供應商間動態分配請求、429 退避<br>• <b>全息記憶</b>：外部記憶 Provider 整合（Mem0、Qdrant 等）<br>• <b>自我學習</b>與自評機制<br><br>適合需要複雜工作流自動化的企業。需要評估您的場景嗎？'
    },
    { keys: ['報價', '多少錢', '費用', '價格', '預算', '收費', 'cost', 'price'],
      answer: '我們採透明計費，依專案規模與複雜度報價：<br><br>一、<b>輕量諮詢</b>：NT$ 15,000 起 — 單一模組、API 串接、提示詞調校，2 週交付<br>二、<b>標準系統</b>：NT$ 80,000 起 — 完整 RAG / Agent 系統、反幻覺設計、正式部署，4-8 週交付（最常選擇）<br>三、<b>企業導入</b>：洽談報價 — 大型 AI 轉型、多部門整合、長期合作<br><br>複雜度高的系統建議先諮詢再確認報價。可至<a href="#pricing">報價方案</a>查看詳情，或<a href="#contact">填寫需求</a>取得精確報價。' },
    { keys: ['流程', '合作', '怎麼開始', '步驟', '進行', '交付', '時程'],
      answer: '合作流程分五階段，每環節都可驗證、不留黑盒子：<br><br>一、<b>需求釐清</b> — 理解業務場景、資料現況與目標<br>二、<b>架構設計</b> — 從目標、風險、邏輯、效能、延展性五面向評估<br>三、<b>原型開發</b> — 快速打造可運作 MVP，標記風險燈號<br>四、<b>壓力測試</b> — 反幻覺檢核、安全路由驗證、事實閘門校準<br>五、<b>部署交付</b> — 正式部署、監控、培訓與文件交付<br><br>交付期視方案而定，輕量約 2 週、標準 4-8 週。準備好開始了嗎？' },
    { keys: ['幻覺', '捏造', '錯誤', '準確', '可靠', 'hallucination', '驗證', '可信'],
      answer: '防幻覺是我們的核心理念——「一條捏造的法條，可能讓書狀被退、讓當事人蒙冤」。智研透過三道機制確保可信：<br><br><b>問題一：AI 說的法條存在嗎？</b><br>強制引用政策會回頭驗證來源是否真實存在、內容是否一致<br><br><b>問題二：使用者情緒激動時還硬推法律？</b><br>安全路由在法律分析前先介入接住人<br><br><b>問題三：AI 不知道時會說不知道嗎？</b><br>事實閘門在資訊不足時標示「待查」或「推論」<br><br>系統已通過 123 項測試驗證。' },
    {
      keys: ['提示詞', 'prompt', '提示', '指令', '調校', '工程'],
      answer: '我們提供系統化提示詞工程服務：<br><br>• <b>鏈式流程設計</b>：語境錨定 → 五維分析 → 壓力檢核 → 最終鍛造<br>• <b>提示詞工業化生產</b>：批量產出高品質提示詞<br>• <b>反幻覺設計</b>：事實閘門、引用政策融入提示<br>• <b>跨模型適配</b>：DeepSeek、Claude、Gemini 各自最佳化<br>• <b>壓力測試</b>：模擬反例與邊界狀況<br><br>我們原創開發了多套提示詞架構系統（含策略夥伴系統、提示詞工廠等）。需要為您的場景客製嗎？'
    },
    { keys: ['案例', '實績', '作品', '做過', 'demo', '示範', '參考'],
      answer: '我們已完成多個實際系統，可於諮詢時提供完整示範：<br><br><b>智研法律 AI 框架</b> — 七層架構、47K 法條 RAG、強制引用、123 項測試通過<br><b>智研 MVP 應用</b> — 法律諮詢、合約產生、法規監控、智慧搜尋等六模組 PWA<br><b>磐石矩陣技能庫</b> — 113 技能、27 類 Agent 多域執行與全息記憶<br><b>AI 接案情報系統</b> — 每日掃描全台外包平台 AI 案源<br><br>歡迎<a href="#contact">預約示範</a>，我們會依您的需求展示對應系統。' },
    {
      keys: ['技術', 'stack', '棧', '工具', '用什麼', '語言', 'python', '框架'],
      answer: '我們的完整技術棧：<br><br>• <b>後端</b>：Python（FastAPI、Flask）<br>• <b>資料庫</b>：SQLite FTS5、Qdrant 向量庫<br>• <b>嵌入模型</b>：BGE-M3、text-embedding-3-large<br>• <b>LLM</b>：DeepSeek、Claude、Gemini 等 OpenAI 相容 API<br>• <b>Agent</b>：Hermes Agent 多技能架構<br>• <b>雲端</b>：GCP、OCI、容器化部署<br>• <b>前端</b>：行動優先 PWA、響應式介面<br>• <b>CI/CD</b>：Git 工作流、CodeQL、自動化測試<br><br>對台灣的法規環境與中文語境有具體認識。'
    },
    { keys: ['聯絡', '聯繫', 'email', '信箱', 'mail', '找你', 'contact'],
      answer: '您可以透過以下方式聯絡我們：<br><br><b>電子郵件</b>：Lucien127@proton.me<br><b>服務區域</b>：台灣桃園，全台遠距合作<br><b>回覆時間</b>：1 個工作天內<br><br>最直接的方式是填寫<a href="#contact">洽談表單</a>，告訴我們您的業務場景與需求，我們會主動聯繫您。' },
    {
      keys: ['你是誰', '智研', '小育', '關於', 'about', '介紹', '誰'],
      answer: '智研（Zhiyan）是台灣的 AI 工程接案服務，由 AI 系統架構師小育主理。<br><br>我們專注於將 AI 研究落地為可用的系統，特別深耕：<br>• 台灣法律 AI 與法規資料處理<br>• 多模型 Agent 編排與路由<br>• 提示詞系統化工程<br>• RAG 檢索增強架構<br><br>核心理念是「讓每個 AI 答案都可追蹤、可驗證、可質疑」。已開發完成的系統皆以可重現研究為核心，並以 MIT 開源授權釋出部分框架。<br><br>有任何需求都歡迎<a href="#contact">洽談</a>。'
    },
    {
      keys: ['謝謝', '感謝', 'thanks', 'thx', '好的', '了解', '收到'],
      answer: '不客氣！如果還有其他問題，隨時可以在這裡問我，或直接到<a href="#contact">洽談表單</a>留下您的需求。我們會在 1 個工作天內回覆您。'
    }
  ];

  function findAnswer(query) {
    const q = query.toLowerCase();
    let best = null, bestScore = 0;
    KB.forEach(function (item) {
      let score = 0;
      item.keys.forEach(function (k) {
        if (q.indexOf(k.toLowerCase()) !== -1) score += k.length;
      });
      if (score > bestScore) { bestScore = score; best = item; }
    });
    if (best && bestScore > 0) return best.answer;
    return null;
  }

  function botReply(query) {
    addTyping();
    const delay = 500 + Math.min(query.length * 25, 700);
    setTimeout(function () {
      removeTyping();
      let answer = findAnswer(query);
      if (!answer) {
        answer = '這個問題我目前沒有完整答案，但我可以幫您轉接。建議直接到<a href="#contact">洽談表單</a>留下您的需求，我們會在 1 個工作天內由專人回覆。您也可以試問：「你們提供哪些服務？」「法律 AI 能做什麼？」「報價大約多少？」';
      }
      addMsg(answer, 'ai');
    }, delay);
  }

  function openChat() {
    chatPanel.classList.add('open');
    chatFab.style.display = 'none';
    if (chatBadge) chatBadge.style.display = 'none';
    if (!chatStarted) {
      chatStarted = true;
      setTimeout(function () {
        addMsg('您好，我是智研 AI 客服。<br><br>我可以為您介紹我們的法律 AI、RAG 系統、Agent 架構等接案服務，也能回答報價與合作流程的問題。<br><br>請問有什麼能協助您的嗎？', 'ai');
      }, 200);
    }
    setTimeout(function () { chatInput && chatInput.focus(); }, 300);
  }

  function closeChat() {
    chatPanel.classList.remove('open');
    chatFab.style.display = 'flex';
  }

  chatFab && chatFab.addEventListener('click', openChat);
  chatClose && chatClose.addEventListener('click', closeChat);

  chatForm && chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    addMsg(escapeHtml(text), 'user');
    chatInput.value = '';
    botReply(text);
  });

  document.querySelectorAll('#chatQuick button').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const q = btn.getAttribute('data-q');
      addMsg(escapeHtml(q), 'user');
      botReply(q);
    });
  });

  /* 自動延遲顯示客服提示（首次造訪） */
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    setTimeout(function () {
      if (!chatStarted && chatBadge) {
        chatBadge.style.animation = 'pulse 2s ease-out';
      }
    }, 6000);
  }

  /* ============ 滾動顯現 ============ */
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.style.opacity = '1';
          en.target.style.transform = 'translateY(0)';
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.card, .cap, .step, .case, .plan, .stat').forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.6s cubic-bezier(0.16,1,0.3,1), transform 0.6s cubic-bezier(0.16,1,0.3,1)';
      io.observe(el);
    });
  }
})();
