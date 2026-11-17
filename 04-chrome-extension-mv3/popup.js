(() => {
  "use strict";

  const STORAGE_KEY = "mv3_enabled";
  const toggle = document.getElementById("toggle-enabled");
  const status = document.getElementById("status");
  const btnOptions = document.getElementById("btn-options");

  // Загрузка состояния из chrome.storage.local
  function loadState() {
    chrome.storage.local.get([STORAGE_KEY], (result) => {
      const enabled = result[STORAGE_KEY] !== false; // по умолчанию включено
      toggle.checked = enabled;
      status.textContent = enabled ? "Включено" : "Выключено";
      status.className = "status " + (enabled ? "on" : "off");
    });
  }

  // Сохранение состояния
  function saveState() {
    const enabled = toggle.checked;
    chrome.storage.local.set({ [STORAGE_KEY]: enabled }, () => {
      status.textContent = enabled ? "Включено" : "Выключено";
      status.className = "status " + (enabled ? "on" : "off");
    });
  }

  toggle.addEventListener("change", saveState);
  btnOptions.addEventListener("click", () => {
    if (chrome.runtime && chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    }
  });

  loadState();
})();