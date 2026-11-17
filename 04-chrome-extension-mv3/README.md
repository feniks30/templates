# 04-chrome-extension-mv3 — каркас расширения Chrome Manifest V3

Готовая заготовка расширения для Chrome/Edge без внешних зависимостей.
Содержит popup, options, background service worker и content script с базовым
обменом сообщениями через `chrome.runtime.sendMessage`.

## Структура

- `manifest.json` — манифест Manifest V3 (разрешения `storage`, `activeTab`).
- `popup.html` / `popup.js` — всплывающее окно с тумблером вкл/выкл, состояние
  сохраняется в `chrome.storage.local`.
- `options.html` / `options.js` — страница настроек с сохранением параметров в
  `chrome.storage.local`.
- `background.js` — service worker, принимает и обрабатывает сообщения.
- `content.js` — скрипт на страницах, обменивается сообщениями с background.

## Установка как распакованное расширение

1. Скопируйте папку `04-chrome-extension-mv3` в рабочую папку заказа.
2. Откройте Chrome и перейдите на `chrome://extensions/`.
3. Включите режим разработчика (переключатель «Режим разработчика» в правом
   верхнем углу).
4. Нажмите «Загрузить распакованное» и выберите папку шаблона.
5. Расширение появится в списке и на панели расширений.

## Адаптация под ТЗ клиента

- **popup** — правьте `popup.html` и `popup.js`: добавьте свои поля и логику,
  состояние хранится через `chrome.storage.local.set/get`.
- **options** — правьте `options.html` и `options.js`: страница настроек тоже
  использует `chrome.storage.local`.
- **content script** — правьте `content.js`: код выполняется на страницах,
  указанных в `manifest.json` (`content_scripts.matches`).
- **background** — правьте `background.js`: service worker для долгоживущих
  задач и обмена сообщениями между popup, options и content script.

## Обмен сообщениями

Пример отправки из content в background:

```js
chrome.runtime.sendMessage({ type: "ping" }, (response) => {
  console.log("Ответ:", response);
});
```

background отвечает в `chrome.runtime.onMessage.addListener`.

## Безопасность

- Реальные ключи и токены не хранятся в коде. Настройки через `chrome.storage.local`
  (локально в браузере пользователя).
- Не передавайте токены в сообщениях между скриптами без необходимости.

## Лицензия

MIT — см. `LICENSE` в корне репозитория шаблонов.