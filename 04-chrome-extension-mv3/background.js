/* background.js — service worker расширения Manifest V3.
 * Принимает и обрабатывает сообщения от popup, options и content script.
 */

(function () {
  "use strict";

  // Хранилище состояния в памяти service worker (для permanentes — chrome.storage.local).
  const state = { enabled: true };

  // Обработка входящих сообщений.
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    try {
      switch (message.type) {
        case "contentReady": {
          console.log("[bg] контент-скрипт готов:", message.url);
          sendResponse({ ok: true, enabled: state.enabled });
          break;
        }
        case "pageClick": {
          console.log("[bg] клик на странице:", message.tag, message.text);
          sendResponse({ ok: true });
          break;
        }
        case "getState": {
          sendResponse({ ok: true, enabled: state.enabled });
          break;
        }
        case "setState": {
          if (typeof message.enabled === "boolean") {
            state.enabled = message.enabled;
            // Сохраняем в локальное хранилище браузера (доступно из popup/options).
            chrome.storage.local.set({ mv3_enabled: state.enabled });
          }
          sendResponse({ ok: true, enabled: state.enabled });
          break;
        }
        default: {
          sendResponse({ ok: false, error: "unknown type: " + message.type });
        }
      }
    } catch (e) {
      sendResponse({ ok: false, error: String(e) });
    }
    // Возвращаем true, чтобы sendResponse можно было вызвать асинхронно (не используется здесь).
    return true;
  });

  console.log("[bg] service worker запущен");
})();