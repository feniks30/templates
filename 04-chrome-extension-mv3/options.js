(() => {
  "use strict";

  const KEYS = ["mv3_interval", "mv3_target"];
  const inpInterval = document.getElementById("inp-interval");
  const inpTarget = document.getElementById("inp-target");
  const btnSave = document.getElementById("btn-save");
  const msg = document.getElementById("msg");

  // Загрузка настроек
  function load() {
    chrome.storage.local.get(KEYS, (result) => {
      inpInterval.value = result.mv3_interval || 60;
      inpTarget.value = result.mv3_target || "";
    });
  }

  // Сохранение настроек
  function save() {
    const values = {
      mv3_interval: parseInt(inpInterval.value, 10) || 60,
      mv3_target: inpTarget.value.trim(),
    };
    chrome.storage.local.set(values, () => {
      msg.textContent = "Настройки сохранены";
      msg.className = "msg ok";
      setTimeout(() => { msg.textContent = ""; msg.className = "msg"; }, 2000);
    });
  }

  btnSave.addEventListener("click", save);
  load();
})();