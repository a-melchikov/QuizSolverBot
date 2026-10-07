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

  // ---------------- Theme Management ----------------
  const THEME_KEY = "quiz_solver_theme";
  function initTheme() {
    let savedTheme = localStorage.getItem(THEME_KEY);
    if (!savedTheme) {
      if (tg?.colorScheme) {
        savedTheme = tg.colorScheme;
      } else {
        savedTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      }
    }
    applyTheme(savedTheme);

    const toggleBtn = document.getElementById("theme-toggle-btn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        triggerHaptic("light");
        const isDark = document.body.classList.contains("theme-dark");
        applyTheme(isDark ? "light" : "dark");
      });
    }
  }

  function applyTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
    const sunIcon = document.getElementById("theme-icon-sun");
    const moonIcon = document.getElementById("theme-icon-moon");

    if (theme === "dark") {
      document.body.classList.add("theme-dark");
      document.body.classList.remove("theme-light");
      if (sunIcon) sunIcon.style.display = "block";
      if (moonIcon) moonIcon.style.display = "none";
      try {
        if (tg) {
          tg.setHeaderColor?.("#1e293b");
          tg.setBackgroundColor?.("#0f172a");
        }
      } catch (_) {}
    } else {
      document.body.classList.add("theme-light");
      document.body.classList.remove("theme-dark");
      if (sunIcon) sunIcon.style.display = "none";
      if (moonIcon) moonIcon.style.display = "block";
      try {
        if (tg) {
          tg.setHeaderColor?.("#ffffff");
          tg.setBackgroundColor?.("#f8fafc");
        }
      } catch (_) {}
    }
  }

  // ---------------- State ----------------
  let currentTab = "quiz";
  let userProfile = null;
  let totalAvailableQuestions = 238;

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
    initTheme();
    setupNavigation();
    setupQuizListeners();
    setupCatalogListeners();
    setupModalListeners();
    await loadInitialData();
  }

  async function loadInitialData() {
    try {
      userProfile = await apiFetch("/api/me");
      userBadge.textContent = userProfile.first_name || userProfile.username || "Пользователь";
    } catch (e) {
      console.warn("Could not load user info:", e);
      userBadge.textContent = "Гость";
    }

    try {
      const qResp = await apiFetch("/api/questions?limit=1");
      if (qResp && qResp.total) {
        totalAvailableQuestions = qResp.total;
        const allChip = document.getElementById("chip-all-count");
        if (allChip) allChip.textContent = `Все (${totalAvailableQuestions})`;
        const hint = document.getElementById("custom-count-hint");
        if (hint) hint.textContent = `Доступно вопросов в базе: ${totalAvailableQuestions}`;
        const input = document.getElementById("custom-count-input");
        if (input) {
          input.max = totalAvailableQuestions;
          input.placeholder = `1–${totalAvailableQuestions}`;
        }
      }
    } catch (_) {}
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
    const customInput = document.getElementById("custom-count-input");

    chips.forEach((c) => {
      c.addEventListener("click", () => {
        chips.forEach((item) => item.classList.remove("active"));
        c.classList.add("active");
        if (customInput) customInput.value = "";

        if (c.dataset.count === "all") {
          quizCount = totalAvailableQuestions;
        } else {
          quizCount = parseInt(c.dataset.count) || 10;
        }
        triggerHaptic("selection");
      });
    });

    if (customInput) {
      customInput.addEventListener("input", () => {
        let val = parseInt(customInput.value);
        if (isNaN(val) || val <= 0) {
          quizCount = 10;
          return;
        }
        if (val > totalAvailableQuestions) {
          val = totalAvailableQuestions;
          customInput.value = val;
        }
        quizCount = val;
        chips.forEach((item) => item.classList.remove("active"));
      });
    }

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
        body: JSON.stringify({
          count: quizCount,
          mode: quizMode,
        }),
      });

      if (!resp.questions || resp.questions.length === 0) {
        alert("Нет доступных вопросов в базе!");
        btn.disabled = false;
        btn.textContent = "Начать тест";
        return;
      }

      activeAttemptId = resp.test_attempt_id;
      activeQuestions = resp.questions;
      currentQIdx = 0;
      userAnswers = {};

      viewSetup.style.display = "none";
      viewActive.style.display = "block";
      viewResults.style.display = "none";

      startTimer();
      renderQuestion();
    } catch (e) {
      alert("Ошибка при запуске теста. Попробуйте снова.");
      console.error(e);
    } finally {
      btn.disabled = false;
      btn.textContent = "Начать тест";
    }
  }

  function startTimer() {
    clearInterval(timerInterval);
    quizStartTime = Date.now();
    const timerElem = document.getElementById("quiz-timer");
    timerElem.textContent = "⏱️ 00:00";

    timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - quizStartTime) / 1000);
      const m = Math.floor(elapsed / 60);
      const s = elapsed % 60;
      timerElem.textContent = `⏱️ ${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}`;
    }, 1000);
  }

  function renderQuestion() {
    const q = activeQuestions[currentQIdx];
    const total = activeQuestions.length;

    // Progress and counter
    document.getElementById("quiz-question-counter").textContent = `Вопрос ${currentQIdx + 1} из ${total}`;
    document.getElementById("quiz-progress-bar").style.width = `${((currentQIdx + 1) / total) * 100}%`;

    // Question text
    document.getElementById("quiz-question-text").textContent = q.text;

    const optContainer = document.getElementById("quiz-options-container");
    const textContainer = document.getElementById("quiz-text-container");
    const feedbackBox = document.getElementById("quiz-feedback-box");
    const btnCheck = document.getElementById("btn-check-answer");
    const btnNext = document.getElementById("btn-next-question");

    optContainer.innerHTML = "";
    feedbackBox.style.display = "none";
    feedbackBox.textContent = "";

    const ansData = userAnswers[q.id] || { selected_option_ids: [], text_answer: "" };

    if (q.has_options) {
      optContainer.style.display = "block";
      textContainer.style.display = "none";

      const isMulti = q.options.filter((o) => o.is_correct).length > 1 || q.options.length > 4;

      q.options.forEach((opt) => {
        const item = document.createElement("div");
        item.className = "option-item";
        item.dataset.optionId = opt.id;

        const isSelected = ansData.selected_option_ids.includes(opt.id);
        if (isSelected) item.classList.add("selected");

        const indicator = document.createElement("div");
        indicator.className = isMulti ? "checkbox-box" : "radio-box";
        indicator.textContent = isSelected ? (isMulti ? "✓" : "●") : "";

        const textSpan = document.createElement("span");
        textSpan.style.flex = "1";
        textSpan.textContent = opt.option_text;

        item.appendChild(indicator);
        item.appendChild(textSpan);

        item.addEventListener("click", () => {
          if (btnNext.style.display === "block" && quizMode === "training") return; // locked after check

          triggerHaptic("selection");
          if (isMulti) {
            if (ansData.selected_option_ids.includes(opt.id)) {
              ansData.selected_option_ids = ansData.selected_option_ids.filter((i) => i !== opt.id);
              item.classList.remove("selected");
              indicator.textContent = "";
            } else {
              ansData.selected_option_ids.push(opt.id);
              item.classList.add("selected");
              indicator.textContent = "✓";
            }
          } else {
            optContainer.querySelectorAll(".option-item").forEach((el) => {
              el.classList.remove("selected");
              el.querySelector(".radio-box").textContent = "";
            });
            ansData.selected_option_ids = [opt.id];
            item.classList.add("selected");
            indicator.textContent = "●";
          }
          userAnswers[q.id] = ansData;
        });

        optContainer.appendChild(item);
      });
    } else {
      optContainer.style.display = "none";
      textContainer.style.display = "block";
      const input = document.getElementById("quiz-text-input");
      input.value = ansData.text_answer || "";
      input.disabled = btnNext.style.display === "block" && quizMode === "training";
      input.oninput = () => {
        ansData.text_answer = input.value;
        userAnswers[q.id] = ansData;
      };
    }

    if (quizMode === "training") {
      btnCheck.style.display = "block";
      btnNext.style.display = "none";
    } else {
      btnCheck.style.display = "none";
      btnNext.style.display = "block";
      btnNext.textContent = currentQIdx === total - 1 ? "Завершить экзамен" : "Следующий вопрос";
    }
  }

  async function checkTrainingAnswer() {
    triggerHaptic("medium");
    const q = activeQuestions[currentQIdx];
    const ansData = userAnswers[q.id] || { selected_option_ids: [], text_answer: "" };

    const btnCheck = document.getElementById("btn-check-answer");
    btnCheck.disabled = true;

    try {
      const resp = await apiFetch("/api/quiz/check-answer", {
        method: "POST",
        body: JSON.stringify({
          question_id: q.id,
          selected_option_ids: ansData.selected_option_ids,
          text_answer: ansData.text_answer,
        }),
      });

      const feedbackBox = document.getElementById("quiz-feedback-box");
      feedbackBox.style.display = "block";

      if (resp.is_correct) {
        triggerHaptic("success");
        feedbackBox.className = "feedback-box correct";
        feedbackBox.innerHTML = "<strong>Верно! Отличный результат.</strong>";
      } else {
        triggerHaptic("error");
        feedbackBox.className = "feedback-box incorrect";
        const correctStr = resp.correct_option_texts.length > 0
          ? resp.correct_option_texts.join(", ")
          : (resp.expected_answer_text || "Не указан");
        feedbackBox.innerHTML = `<strong>Неверно.</strong> Правильный ответ: <em>${escapeHtml(correctStr)}</em>`;
      }

      if (q.has_options) {
        const items = document.querySelectorAll("#quiz-options-container .option-item");
        items.forEach((item) => {
          const optId = parseInt(item.dataset.optionId);
          if (resp.correct_option_ids.includes(optId)) {
            item.classList.add("correct");
          } else if (ansData.selected_option_ids.includes(optId)) {
            item.classList.add("incorrect");
          }
        });
      }

      btnCheck.style.display = "none";
      const btnNext = document.getElementById("btn-next-question");
      btnNext.style.display = "block";
      btnNext.textContent = currentQIdx === activeQuestions.length - 1 ? "Посмотреть результаты" : "Следующий вопрос";
    } catch (e) {
      console.error(e);
      alert("Не удалось проверить ответ.");
    } finally {
      btnCheck.disabled = false;
    }
  }

  function nextQuestion() {
    triggerHaptic("light");
    if (currentQIdx < activeQuestions.length - 1) {
      currentQIdx++;
      renderQuestion();
    } else {
      finishQuiz();
    }
  }

  async function finishQuiz() {
    clearInterval(timerInterval);
    triggerHaptic("success");

    const answersPayload = activeQuestions.map((q) => {
      const ans = userAnswers[q.id] || {};
      return {
        question_id: q.id,
        selected_option_ids: ans.selected_option_ids || [],
        text_answer: ans.text_answer || "",
      };
    });

    try {
      const result = await apiFetch("/api/quiz/finish", {
        method: "POST",
        body: JSON.stringify({
          test_attempt_id: activeAttemptId,
          answers: answersPayload,
        }),
      });

      renderResults(result);
    } catch (e) {
      console.error(e);
      alert("Ошибка завершения теста.");
    }
  }

  function renderResults(result) {
    viewActive.style.display = "none";
    viewResults.style.display = "block";

    const scoreCircle = document.getElementById("result-score-circle");
    scoreCircle.textContent = `${result.percentage}%`;
    if (result.percentage >= 70) {
      scoreCircle.style.color = "var(--success-color)";
    } else if (result.percentage >= 40) {
      scoreCircle.style.color = "var(--warning-color)";
    } else {
      scoreCircle.style.color = "var(--danger-color)";
    }

    const min = Math.floor(result.duration_seconds / 60);
    const sec = result.duration_seconds % 60;
    const durStr = `${min}:${sec < 10 ? "0" : ""}${sec}`;

    document.getElementById("result-summary-text").textContent =
      `Правильных ответов: ${result.score} из ${result.total_questions}`;
    document.getElementById("result-meta").textContent =
      `Время прохождения: ${durStr} • Режим: ${quizMode === "training" ? "Тренировка" : "Экзамен"}`;

    const reviewContainer = document.getElementById("quiz-reviews-container");
    reviewContainer.innerHTML = "";

    result.reviews.forEach((r, idx) => {
      const item = document.createElement("div");
      item.className = "accordion-item";

      const isOk = r.is_correct;
      const statusIcon = isOk ? "✅" : "❌";

      item.innerHTML = `
        <div class="accordion-header">
          <span style="font-weight: 500; font-size: 14px; max-width: 85%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${statusIcon} ${idx + 1}. ${escapeHtml(r.text)}
          </span>
          <span style="font-size: 18px;">⌄</span>
        </div>
        <div class="accordion-body" style="display: none;">
          <p style="font-weight: 600; margin-bottom: 8px;">${escapeHtml(r.text)}</p>
          <div style="font-size: 13px; margin-bottom: 4px;">
            <span style="color: var(--hint-color);">Ваш ответ:</span>
            <strong style="color: ${isOk ? 'var(--success-color)' : 'var(--danger-color)'};">${escapeHtml(r.user_answer || "—")}</strong>
          </div>
          ${!isOk ? `
            <div style="font-size: 13px;">
              <span style="color: var(--hint-color);">Правильный ответ:</span>
              <strong style="color: var(--success-color);">${escapeHtml(r.correct_answer)}</strong>
            </div>
          ` : ""}
        </div>
      `;

      const header = item.querySelector(".accordion-header");
      const body = item.querySelector(".accordion-body");
      header.addEventListener("click", () => {
        const isOpen = body.style.display === "block";
        body.style.display = isOpen ? "none" : "block";
        header.querySelector("span:last-child").textContent = isOpen ? "⌄" : "⌃";
        triggerHaptic("selection");
      });

      reviewContainer.appendChild(item);
    });
  }

  // ---------------- Catalog Tab ----------------
  function setupCatalogListeners() {
    const searchInput = document.getElementById("catalog-search-input");
    let debounceTimeout = null;

    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        catalogQuery = searchInput.value.trim();
        catalogPage = 1;
        loadCatalog(true);
      }, 300);
    });

    const filterChips = document.querySelectorAll(".catalog-filter");
    filterChips.forEach((chip) => {
      chip.addEventListener("click", () => {
        filterChips.forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        catalogFilter = chip.dataset.type;
        catalogPage = 1;
        triggerHaptic("selection");
        loadCatalog(true);
      });
    });

    document.getElementById("btn-load-more").addEventListener("click", () => {
      catalogPage++;
      loadCatalog(false);
    });
  }

  async function loadCatalog(reset = false) {
    const container = document.getElementById("catalog-list-container");
    if (reset) {
      container.innerHTML = "<p style='color: var(--hint-color); text-align: center; padding: 20px;'>Загрузка вопросов...</p>";
    }

    try {
      let url = `/api/questions?page=${catalogPage}&per_page=15`;
      if (catalogQuery) url += `&q=${encodeURIComponent(catalogQuery)}`;
      if (catalogFilter === "options") url += `&has_options=true`;
      if (catalogFilter === "text") url += `&has_options=false`;

      const data = await apiFetch(url);
      catalogTotalPages = data.total_pages;

      document.getElementById("catalog-count-info").textContent = `Найдено вопросов: ${data.total}`;

      if (reset) container.innerHTML = "";

      if (data.items.length === 0 && reset) {
        container.innerHTML = "<p style='color: var(--hint-color); text-align: center; padding: 20px;'>Вопросы не найдены.</p>";
        document.getElementById("btn-load-more").style.display = "none";
        return;
      }

      data.items.forEach((q) => {
        const card = document.createElement("div");
        card.className = "accordion-item";

        let answersHtml = "";
        if (q.has_options && q.options.length > 0) {
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

  // ---------------- Profile & History Details ----------------
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
        card.className = "history-item-card";

        const attemptNum = historyResp.total - idx;
        const dateStr = item.created_at
          ? new Date(item.created_at).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
          : "—";

        const badgeClass = item.percentage >= 70 ? "high" : (item.percentage < 40 ? "low" : "");

        card.innerHTML = `
          <div class="history-card-left">
            <div class="history-card-title">Попытка #${attemptNum}</div>
            <div class="history-card-subtitle">${dateStr} • ${item.score} из ${item.total_questions} вопр.</div>
          </div>
          <div class="history-card-right">
            <span class="history-score-badge ${badgeClass}">${item.percentage}%</span>
            <svg class="history-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </div>
        `;

        card.addEventListener("click", () => {
          openAttemptDetails(item.id, attemptNum);
        });

        listContainer.appendChild(card);
      });
    } catch (e) {
      console.error("Profile load error:", e);
    }
  }

  function openAttemptDetails(attemptId, attemptNum) {
    triggerHaptic("medium");
    const modal = document.getElementById("history-modal");
    const title = document.getElementById("modal-attempt-title");
    const subtitle = document.getElementById("modal-attempt-subtitle");
    const body = document.getElementById("modal-attempt-body");

    title.textContent = `Разбор попытки #${attemptNum || attemptId}`;
    subtitle.textContent = "Загрузка данных...";
    body.innerHTML = "<p style='text-align: center; color: var(--hint-color); padding: 30px;'>Загрузка деталей...</p>";
    modal.style.display = "flex";

    apiFetch(`/api/history/${attemptId}`)
      .then((data) => {
        const dateStr = data.created_at
          ? new Date(data.created_at).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
          : "—";
        const min = Math.floor((data.duration_seconds || 0) / 60);
        const sec = (data.duration_seconds || 0) % 60;
        const durStr = `${min}:${sec < 10 ? '0' : ''}${sec}`;

        subtitle.textContent = `${dateStr} • Результат: ${data.score}/${data.total_questions} (${data.percentage}%) • Время: ${durStr}`;

        if (!data.answers || data.answers.length === 0) {
          body.innerHTML = "<p style='text-align: center; color: var(--hint-color); padding: 20px;'>В этой попытке нет записанных ответов.</p>";
          return;
        }

        body.innerHTML = data.answers.map((ans, idx) => {
          const statusClass = ans.is_correct ? "correct" : "incorrect";
          const statusLabel = ans.is_correct ? "Верно ✓" : "Ошибка ✗";

          let optsHtml = "";
          if (ans.has_options && ans.options && ans.options.length > 0) {
            optsHtml = `<div class="modal-q-options">` +
              ans.options.map((opt, oIdx) => `
                <div class="modal-opt ${opt.is_correct ? 'is-correct' : ''}">
                  ${opt.is_correct ? '✅ ' : '• '}${oIdx + 1}. ${escapeHtml(opt.option_text)}
                </div>
              `).join("") +
              `</div>`;
          } else {
            optsHtml = `
              <div style="margin-top: 8px; font-size: 13px;">
                <span style="color: var(--hint-color);">Правильный ответ:</span>
                <strong style="color: var(--success-color);">${escapeHtml(ans.correct_answer || "—")}</strong>
              </div>
            `;
          }

          return `
            <div class="modal-q-item">
              <div class="modal-q-header">
                <span class="modal-q-text">${idx + 1}. ${escapeHtml(ans.text)}</span>
                <span class="modal-status-badge ${statusClass}">${statusLabel}</span>
              </div>
              ${optsHtml}
            </div>
          `;
        }).join("");
      })
      .catch((err) => {
        console.error("Failed to load attempt details:", err);
        body.innerHTML = "<p style='text-align: center; color: var(--danger-color); padding: 20px;'>Не удалось загрузить данные попытки.</p>";
      });
  }

  function setupModalListeners() {
    const modal = document.getElementById("history-modal");
    const closeBtn = document.getElementById("modal-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        triggerHaptic("light");
        modal.style.display = "none";
      });
    }
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          triggerHaptic("light");
          modal.style.display = "none";
        }
      });
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
