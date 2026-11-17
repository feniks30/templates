/* content.js — скрипт, выполняющийся на страницах (manifest: content_scripts).
 * Базовый обмен сообщениями с background через chrome.runtime.sendMessage.
 */

(function () {
  "use strict";

  // Сообщаем background, что контент-скрипт загрузился на этой странице.
  try {
    chrome.runtime.sendMessage({ type: "contentReady", url: window.location.href });
  } catch (e) {
    // Расширение может быть недоступно в некоторых контекстах — молча игнорируем.
  }

  // Пример: при клике по странице отправляем событие в background.
  document.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!target || !target.tagName) return;
    chrome.runtime.sendMessage({
      type: "pageClick",
      tag: target.tagName,
      text: (target.innerText || "").trim().slice(0, 120),
      url: window.location.href,
    });
  });
})();