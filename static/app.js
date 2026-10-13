/* ============================================================
   GAME STUDIO 8-BIT — lógica de geração de vídeo (vanilla JS)
   ============================================================ */

(function () {
  "use strict";

  const API = "/api/v1/jobs";
  const POLL_MS = 3000;
  const BAR_MS = 350;
  const BAR_TOTAL = 6;
  const MAX_POLLS = 200; // trava de segurança

  // Elementos
  const formSection = document.getElementById("form-section");
  const loadingSection = document.getElementById("loading-section");
  const gameoverSection = document.getElementById("gameover-section");
  const successSection = document.getElementById("success-section");
  const promptInput = document.getElementById("prompt");
  const startBtn = document.getElementById("start-btn");
  const retryBtn = document.getElementById("retry-btn");
  const againBtn = document.getElementById("again-btn");
  const loadingBar = document.getElementById("loading-bar");
  const loadingStatus = document.getElementById("loading-status");
  const errorMsg = document.getElementById("error-msg");
  const player = document.getElementById("player");

  let pollTimer = null;
  let barTimer = null;
  let polls = 0;

  function show(el) {
    el.classList.remove("hidden");
  }

  function hide(el) {
    el.classList.add("hidden");
  }

  function showOnly(section) {
    [formSection, loadingSection, gameoverSection, successSection].forEach(hide);
    show(section);
  }

  function renderBar(step) {
    const filled = Math.min(BAR_TOTAL, step);
    loadingBar.textContent =
      "[" + "■".repeat(filled) + "□".repeat(BAR_TOTAL - filled) + "]";
  }

  function startLoadingAnimation() {
    stopLoadingAnimation();
    let step = 0;
    renderBar(step);
    barTimer = setInterval(() => {
      step = step >= BAR_TOTAL ? 1 : step + 1;
      renderBar(step);
    }, BAR_MS);
  }

  function stopLoadingAnimation() {
    if (barTimer) {
      clearInterval(barTimer);
      barTimer = null;
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function cleanup() {
    stopPolling();
    stopLoadingAnimation();
  }

  // ---- Envio do formulário ----
  async function submitForm() {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      promptInput.focus();
      promptInput.placeholder = "DIGITE UM PROMPT PRIMEIRO!";
      return;
    }

    startBtn.disabled = true;
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt }),
      });
      if (res.status !== 202 && !res.ok) {
        throw new Error("Falha ao criar job (HTTP " + res.status + ")");
      }
      const job = await res.json();
      startPolling(job.id);
    } catch (err) {
      cleanup();
      showError(err.message || String(err));
    } finally {
      startBtn.disabled = false;
    }
  }

  // ---- Polling de status ----
  function startPolling(jobId) {
    showOnly(loadingSection);
    startLoadingAnimation();
    loadingStatus.textContent = "NA FILA...";
    polls = 0;
    pollStatus(jobId);
    pollTimer = setInterval(() => pollStatus(jobId), POLL_MS);
  }

  async function pollStatus(jobId) {
    polls += 1;
    if (polls > MAX_POLLS) {
      cleanup();
      showError("Tempo esgotado — tente novamente.");
      return;
    }
    try {
      const res = await fetch(API + "/" + jobId);
      if (!res.ok) {
        throw new Error("Erro ao consultar job (HTTP " + res.status + ")");
      }
      const job = await res.json();
      switch (job.status) {
        case "pending":
          loadingStatus.textContent = "NA FILA...";
          break;
        case "processing":
          loadingStatus.textContent = "PROCESSANDO MAGIA...";
          break;
        case "failed":
          cleanup();
          showError(job.error_message || "Erro desconhecido durante a geração.");
          break;
        case "completed":
          cleanup();
          showSuccess(job.output_url);
          break;
      }
    } catch (err) {
      // Mantém o polling em falha transatória de rede, mas reporta em tela
      loadingStatus.textContent = "RECONECTANDO...";
    }
  }

  // ---- Telas ----
  function showError(message) {
    errorMsg.textContent = message;
    showOnly(gameoverSection);
  }

  function showSuccess(outputUrl) {
    player.src = outputUrl || "";
    player.load();
    showOnly(successSection);
  }

  function reset() {
    cleanup();
    player.pause();
    player.removeAttribute("src");
    player.load();
    promptInput.value = "";
    showOnly(formSection);
  }

  // ---- Eventos ----
  startBtn.addEventListener("click", submitForm);
  retryBtn.addEventListener("click", reset);
  againBtn.addEventListener("click", reset);
  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitForm();
    }
  });
})();
