(() => {
  // Telegram WebApp Setup
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  function triggerHaptic(type = "light") {
    try {
      if (tg?.HapticFeedback) {
        if (type === "success" || type === "error" || type === "warning") {
          tg.HapticFeedback.notificationOccurred(type);
        } else {
          tg.HapticFeedback.impactOccurred(type);
        }
      }
    } catch (_) {}
  }

  const API_BASE = "";
  function getHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (tg?.initData) {
      headers["Authorization"] = `tma ${tg.initData}`;
    }
    return headers;
  }

  async function apiFetch(url, options = {}) {
    options.headers = { ...getHeaders(), ...(options.headers || {}) };
    const res = await fetch(`${API_BASE}${url}`, options);
    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }
    return res.json();
  }

  // State
  let currentTab = "quiz";
  let userProfile = null;

  // Quiz State
  let quizMode = "training"; // "training" or "exam"
  let quizCount = 10;
  let activeAttemptId = null;
  let activeQuestions = [];
  let currentQIdx = 0;
  let userAnswers = {}; // { qId: { selected_option_ids: [], text_answer: "" } }
  let timerInterval = null;
  let quizStartTime = null;

  // Catalog State
  let catalogPage = 1;
  let catalogQuery = "";
  let catalogFilter = "all";
  let catalogTotalPages = 1;

  // DOM Elements
  const tabQuiz = document.getElementById("tab-quiz");
  const tabCatalog = document.getElementById("tab-catalog");
  const tabProfile = document.getElementById("tab-profile");
  const navTabs = document.querySelectorAll(".nav-tab");
  const userBadge = document.getElementById("user-badge");

  // Views in Quiz Tab
  const viewSetup = document.getElementById("quiz-setup-view");
  const viewActive = document.getElementById("quiz-active-view");
  const viewResults = document.getElementById("quiz-results-view");

  // Init
  async function init() {
    setupNavigation();
    setupQuizListeners();
    setupCatalogListeners();

    try {
      userProfile = await apiFetch("/api/me");
      userBadge.textContent = userProfile.first_name || userProfile.username || "Пользователь";
    } catch (e) {
      console.warn("Could not load user info:", e);
      userBadge.textContent = "Гость";
    }
  }

  // ---------------- Navigation ----------------
  function setupNavigation() {
    navTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const target = tab.dataset.tab;
        switchTab(target);
      });
    });
  }

  function switchTab(tabName) {
    if (currentTab === tabName) return;
    triggerHaptic("light");
    currentTab = tabName;

    navTabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
    tabQuiz.style.display = tabName === "quiz" ? "block" : "none";
    tabCatalog.style.display = tabName === "catalog" ? "block" : "none";
    tabProfile.style.display = tabName === "profile" ? "block" : "none";

    if (tabName === "catalog") {
      loadCatalog(true);
    } else if (tabName === "profile") {
      loadProfile();
    }
  }

  // ---------------- Quiz Tab ----------------
  function setupQuizListeners() {
    // Count chips
    const chips = document.querySelectorAll("#count-selector .chip");
    chips.forEach((c) => {
      c.addEventListener("click", () => {
        chips.forEach((item) => item.classList.remove("active"));
        c.classList.add("active");
        quizCount = parseInt(c.dataset.count);
        triggerHaptic("selection");
      });
    });

    // Mode selector
    const modeTraining = document.getElementById("mode-training");
    const modeExam = document.getElementById("mode-exam");
    modeTraining.addEventListener("click", () => {
      modeTraining.classList.add("selected");
      modeExam.classList.remove("selected");
      quizMode = "training";
      triggerHaptic("selection");
    });
    modeExam.addEventListener("click", () => {
      modeExam.classList.add("selected");
      modeTraining.classList.remove("selected");
      quizMode = "exam";
      triggerHaptic("selection");
    });

    document.getElementById("btn-start-quiz").addEventListener("click", startQuiz);
    document.getElementById("btn-check-answer").addEventListener("click", checkTrainingAnswer);
    document.getElementById("btn-next-question").addEventListener("click", nextQuestion);
    document.getElementById("btn-cancel-quiz").addEventListener("click", () => {
      if (confirm("Завершить тестирование сейчас?")) {
        finishQuiz();
      }
    });
    document.getElementById("btn-restart-quiz").addEventListener("click", () => {
      viewResults.style.display = "none";
      viewSetup.style.display = "block";
    });
  }

  async function startQuiz() {
    triggerHaptic("medium");
    const btn = document.getElementById("btn-start-quiz");
    btn.disabled = true;
    btn.textContent = "Загрузка...";

    try {
      const resp = await apiFetch("/api/quiz/start", {
        method: "POST",
        body: JSON.stringify({ count: quizCount, mode: quizMode }),
      });

      if (!resp.questions || resp.questions.length === 0) {
        alert("В базе данных нет доступных вопросов!");
        return;
      }

      activeAttemptId = resp.test_attempt_id;
      activeQuestions = resp.questions;
      currentQIdx = 0;
      userAnswers = {};

      viewSetup.style.display = "none";
      viewResults.style.display = "none";
      viewActive.style.display = "block";

      startTimer();
      renderActiveQuestion();
    } catch (e) {
      alert("Ошибка при старте теста: " + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Начать тест";
    }
  }

  function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    quizStartTime = Date.now();
    const timerElem = document.getElementById("quiz-timer");

    timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - quizStartTime) / 1000);
      const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const s = String(elapsed % 60).padStart(2, "0");
      timerElem.textContent = `⏱️ ${m}:${s}`;
    }, 1000);
  }

  function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
  }

  function renderActiveQuestion() {
    const q = activeQuestions[currentQIdx];
    const total = activeQuestions.length;

    // Progress bar and counter
    const pct = ((currentQIdx + 1) / total) * 100;
    document.getElementById("quiz-progress-bar").style.width = `${pct}%`;
    document.getElementById("quiz-question-counter").textContent = `Вопрос ${currentQIdx + 1} из ${total}`;

    document.getElementById("quiz-question-text").textContent = q.text;

    const optionsContainer = document.getElementById("quiz-options-container");
    const textContainer = document.getElementById("quiz-text-container");
    const feedbackBox = document.getElementById("quiz-feedback-box");
    const btnCheck = document.getElementById("btn-check-answer");
    const btnNext = document.getElementById("btn-next-question");

    optionsContainer.innerHTML = "";
    feedbackBox.style.display = "none";
    feedbackBox.className = "feedback-box";

    // Setup input answer holder
    if (!userAnswers[q.id]) {
      userAnswers[q.id] = { selected_option_ids: [], text_answer: "" };
    }

    if (q.has_options) {
      optionsContainer.style.display = "block";
      textContainer.style.display = "none";

      q.options.forEach((opt) => {
        const item = document.createElement("div");
        item.className = "option-item";
        item.dataset.optionId = opt.id;

        const isMulti = q.options.filter((o) => o.is_correct).length > 1;
        const boxClass = isMulti ? "checkbox-box" : "radio-box";
        item.innerHTML = `<span class="${boxClass}"></span><span>${escapeHtml(opt.option_text)}</span>`;

        if (userAnswers[q.id].selected_option_ids.includes(opt.id)) {
          item.classList.add("selected");
        }

        item.addEventListener("click", () => {
          triggerHaptic("selection");
          if (quizMode === "training" && feedbackBox.style.display === "block") {
            return; // locked after check in training mode
          }

          if (isMulti) {
            item.classList.toggle("selected");
            const sel = userAnswers[q.id].selected_option_ids;
            const idx = sel.indexOf(opt.id);
            if (idx > -1) sel.splice(idx, 1);
            else sel.push(opt.id);
          } else {
            optionsContainer.querySelectorAll(".option-item").forEach((el) => el.classList.remove("selected"));
            item.classList.add("selected");
            userAnswers[q.id].selected_option_ids = [opt.id];
          }
        });

        optionsContainer.appendChild(item);
      });
    } else {
      optionsContainer.style.display = "none";
      textContainer.style.display = "block";
      const input = document.getElementById("quiz-text-input");
      input.value = userAnswers[q.id].text_answer || "";
      input.disabled = false;
      input.oninput = (e) => {
        userAnswers[q.id].text_answer = e.target.value;
      };
    }

    if (quizMode === "training") {
      btnCheck.style.display = "block";
      btnNext.style.display = "none";
    } else {
      btnCheck.style.display = "none";
      btnNext.style.display = "block";
      btnNext.textContent = currentQIdx === total - 1 ? "Завершить тест" : "Следующий вопрос";
    }
  }

  async function checkTrainingAnswer() {
    const q = activeQuestions[currentQIdx];
    const answer = userAnswers[q.id];

    if (q.has_options && (!answer.selected_option_ids || answer.selected_option_ids.length === 0)) {
      alert("Пожалуйста, выберите вариант ответа.");
      return;
    }
    if (!q.has_options && (!answer.text_answer || !answer.text_answer.trim())) {
      alert("Пожалуйста, введите ответ.");
      return;
    }

    const btnCheck = document.getElementById("btn-check-answer");
    btnCheck.disabled = true;

    try {
      const resp = await apiFetch("/api/quiz/check-answer", {
        method: "POST",
        body: JSON.stringify({
          question_id: q.id,
          selected_option_ids: answer.selected_option_ids,
          text_answer: answer.text_answer,
        }),
      });

      const feedbackBox = document.getElementById("quiz-feedback-box");
      const btnNext = document.getElementById("btn-next-question");

      if (resp.is_correct) {
        triggerHaptic("success");
        feedbackBox.className = "feedback-box correct";
        feedbackBox.textContent = "✅ Правильно! Отличный результат.";
      } else {
        triggerHaptic("error");
        feedbackBox.className = "feedback-box incorrect";
        const correctInfo = resp.correct_option_texts.length > 0
          ? resp.correct_option_texts.join(", ")
          : resp.expected_answer_text;
        feedbackBox.innerHTML = `❌ Неверно.<br><strong>Правильный ответ:</strong> ${escapeHtml(correctInfo)}`;
      }

      // Highlight options if options exist
      if (q.has_options) {
        document.querySelectorAll(".option-item").forEach((el) => {
          const optId = parseInt(el.dataset.optionId);
          if (resp.correct_option_ids.includes(optId)) {
            el.classList.add("correct");
          } else if (answer.selected_option_ids.includes(optId)) {
            el.classList.add("incorrect");
          }
        });
      } else {
        document.getElementById("quiz-text-input").disabled = true;
      }

      feedbackBox.style.display = "block";
      btnCheck.style.display = "none";
      btnNext.style.display = "block";
      btnNext.textContent = currentQIdx === activeQuestions.length - 1 ? "Завершить тест" : "Следующий вопрос";
    } catch (e) {
      alert("Ошибка при проверке ответа: " + e.message);
    } finally {
      btnCheck.disabled = false;
    }
  }

  function nextQuestion() {
    triggerHaptic("light");
    if (currentQIdx < activeQuestions.length - 1) {
      currentQIdx++;
      renderActiveQuestion();
    } else {
      finishQuiz();
    }
  }

  async function finishQuiz() {
    stopTimer();
    triggerHaptic("medium");

    const payload = {
      test_attempt_id: activeAttemptId,
      answers: activeQuestions.map((q) => ({
        question_id: q.id,
        selected_option_ids: userAnswers[q.id]?.selected_option_ids || [],
        text_answer: userAnswers[q.id]?.text_answer || "",
      })),
    };

    try {
      const resp = await apiFetch("/api/quiz/finish", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      renderResults(resp);
    } catch (e) {
      alert("Ошибка при сохранении результатов: " + e.message);
    }
  }

  function renderResults(resp) {
    viewActive.style.display = "none";
    viewResults.style.display = "block";

    const scoreCircle = document.getElementById("result-score-circle");
    scoreCircle.textContent = `${resp.percentage}%`;
    scoreCircle.style.color = resp.percentage >= 70 ? "var(--success-color)" : (resp.percentage >= 40 ? "var(--warning-color)" : "var(--danger-color)");

    document.getElementById("result-summary-text").textContent = `Правильных ответов: ${resp.score} из ${resp.total_questions}`;

    const m = Math.floor(resp.duration_seconds / 60);
    const s = resp.duration_seconds % 60;
    document.getElementById("result-meta").textContent = `Время выполнения: ${m} мин ${s} сек`;

    const container = document.getElementById("quiz-reviews-container");
    container.innerHTML = "";

    resp.reviews.forEach((rev, idx) => {
      const item = document.createElement("div");
      item.className = "accordion-item";

      const icon = rev.is_correct ? "✅" : "❌";
      const statusColor = rev.is_correct ? "var(--success-color)" : "var(--danger-color)";

      item.innerHTML = `
        <div class="accordion-header" style="color: ${statusColor};">
          <span>${icon} Вопрос ${idx + 1}</span>
          <span style="font-size: 13px; color: var(--hint-color);">${rev.is_correct ? "Верно" : "Ошибка"}</span>
        </div>
        <div class="accordion-body">
          <p style="font-weight: 600; margin-bottom: 8px;">${escapeHtml(rev.text)}</p>
          <p style="font-size: 13px; margin-bottom: 4px;">Ваш ответ: <span style="color: ${statusColor};">${escapeHtml(rev.user_answer || "—")}</span></p>
          ${!rev.is_correct ? `<p style="font-size: 13px; color: var(--success-color);">Правильный: <b>${escapeHtml(rev.correct_answer)}</b></p>` : ""}
        </div>
      `;
      container.appendChild(item);
    });
  }

  // ---------------- Catalog Tab ----------------
  function setupCatalogListeners() {
    const searchInput = document.getElementById("catalog-search-input");
    let debounceTimeout = null;

    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        catalogQuery = e.target.value.trim();
        loadCatalog(true);
      }, 300);
    });

    const filters = document.querySelectorAll(".catalog-filter");
    filters.forEach((f) => {
      f.addEventListener("click", () => {
        filters.forEach((el) => el.classList.remove("active"));
        f.classList.add("active");
        catalogFilter = f.dataset.type;
        triggerHaptic("selection");
        loadCatalog(true);
      });
    });

    document.getElementById("btn-load-more").addEventListener("click", () => {
      if (catalogPage < catalogTotalPages) {
        catalogPage++;
        loadCatalog(false);
      }
    });
  }

  async function loadCatalog(reset = false) {
    if (reset) {
      catalogPage = 1;
      document.getElementById("catalog-list-container").innerHTML = "<p style='color: var(--hint-color); padding: 10px;'>Загрузка...</p>";
    }

    let url = `/api/questions?page=${catalogPage}&limit=15`;
    if (catalogQuery) url += `&q=${encodeURIComponent(catalogQuery)}`;
    if (catalogFilter === "options") url += "&has_options=true";
    if (catalogFilter === "text") url += "&has_options=false";

    try {
      const resp = await apiFetch(url);
      catalogTotalPages = resp.total_pages;

      document.getElementById("catalog-count-info").textContent = `Найдено вопросов: ${resp.total}`;
      const container = document.getElementById("catalog-list-container");

      if (reset) container.innerHTML = "";

      if (resp.items.length === 0 && reset) {
        container.innerHTML = "<p style='color: var(--hint-color); text-align: center; padding: 20px;'>Вопросы не найдены.</p>";
        document.getElementById("btn-load-more").style.display = "none";
        return;
      }

      resp.items.forEach((q) => {
        const card = document.createElement("div");
        card.className = "accordion-item";

        let answersHtml = "";
        if (q.has_options) {
          answersHtml = q.options.map((opt, i) => `
            <div style="margin-bottom: 4px; ${opt.is_correct ? 'color: var(--success-color); font-weight: 600;' : 'color: var(--hint-color);'}">
              ${opt.is_correct ? '✅' : '•'} ${i + 1}. ${escapeHtml(opt.option_text)}
            </div>
          `).join("");
        } else {
          answersHtml = `<div style="color: var(--success-color); font-weight: 600;">Ответ: ${escapeHtml(q.answer_text || "Не указан")}</div>`;
        }

        card.innerHTML = `
          <div class="accordion-header">
            <span style="font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 85%;">
              #${q.id} ${escapeHtml(q.text)}
            </span>
            <span style="font-size: 18px;">⌄</span>
          </div>
          <div class="accordion-body" style="display: none;">
            <p style="font-weight: 600; margin-bottom: 10px;">${escapeHtml(q.text)}</p>
            ${answersHtml}
          </div>
        `;

        const header = card.querySelector(".accordion-header");
        const body = card.querySelector(".accordion-body");
        header.addEventListener("click", () => {
          const isOpen = body.style.display === "block";
          body.style.display = isOpen ? "none" : "block";
          header.querySelector("span:last-child").textContent = isOpen ? "⌄" : "⌃";
          triggerHaptic("selection");
        });

        container.appendChild(card);
      });

      document.getElementById("btn-load-more").style.display = catalogPage < catalogTotalPages ? "block" : "none";
    } catch (e) {
      console.error("Catalog load error:", e);
    }
  }

  // ---------------- Profile Tab ----------------
  async function loadProfile() {
    try {
      const me = await apiFetch("/api/me");
      document.getElementById("stat-completed").textContent = me.completed_attempts;
      document.getElementById("stat-avg").textContent = `${me.avg_percentage}%`;

      const historyResp = await apiFetch("/api/history?limit=15");
      const listContainer = document.getElementById("history-list-container");
      listContainer.innerHTML = "";

      if (historyResp.items.length === 0) {
        listContainer.innerHTML = "<p style='color: var(--hint-color); text-align: center; padding: 20px;'>Вы ещё не завершили ни одного теста.</p>";
        return;
      }

      historyResp.items.forEach((item, idx) => {
        const card = document.createElement("div");
        card.className = "card";
        card.style.padding = "12px 16px";
        card.style.marginBottom = "8px";

        const dateStr = item.created_at ? new Date(item.created_at).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
        const color = item.percentage >= 70 ? "var(--success-color)" : (item.percentage >= 40 ? "var(--warning-color)" : "var(--danger-color)");

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; font-size: 15px;">Попытка #${historyResp.total - idx}</div>
              <div style="font-size: 12px; color: var(--hint-color);">${dateStr}</div>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 18px; font-weight: 700; color: ${color};">${item.percentage}%</div>
              <div style="font-size: 12px; color: var(--hint-color);">${item.score} из ${item.total_questions}</div>
            </div>
          </div>
        `;
        listContainer.appendChild(card);
      });
    } catch (e) {
      console.error("Profile load error:", e);
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  document.addEventListener("DOMContentLoaded", init);
})();
