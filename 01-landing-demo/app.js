'use strict';

// ==================== МОК-ДАННЫЕ ====================
const SERVICES = [
  { title: 'Лендинг под ключ', price: 'от 45 000 ₽', desc: 'Одностраничный сайт с адаптивом, анимацией и формой заявки.' },
  { title: 'Корпоративный сайт', price: 'от 150 000 ₽', desc: 'Многостраничный ресурс с каталогом услуг, блогом и админ-панелью.' },
  { title: 'Интернет-магазин', price: 'от 300 000 ₽', desc: 'Торговая платформа с каталогом, корзиной, онлайн-оплатой и личным кабинетом.' },
];

const TARIFFS = [
  { name: 'Старт', price: 45000, features: ['Одностраничный сайт', 'Адаптив под мобилки', 'Форма обратной связи', 'Поддержка 14 дней'] },
  { name: 'Бизнес', price: 120000, features: ['Многостраничный сайт', 'Адаптив под мобилки', 'SEO-оптимизация', 'Форма обратной связи', 'Поддержка 30 дней'] },
  { name: 'Премиум', price: 250000, features: ['Интернет-магазин', 'Личный кабинет', 'Онлайн-оплата', 'SEO-оптимизация', 'Поддержка 90 дней'] },
];

const CATALOG = [
  { id: 1, title: 'Сайт агентства', category: 'web', price: '60 000 ₽' },
  { id: 2, title: 'Лендинг для события', category: 'web', price: '45 000 ₽' },
  { id: 3, title: 'Брендбук и логотип', category: 'design', price: '35 000 ₽' },
  { id: 4, title: 'Макет мобильного приложения', category: 'design', price: '55 000 ₽' },
  { id: 5, title: 'Рекламная кампания', category: 'marketing', price: '40 000 ₽' },
  { id: 6, title: 'SMM-стратегия', category: 'marketing', price: '30 000 ₽' },
];

const BASE_PRICES = { landing: 50000, corporate: 150000, store: 300000 };

// ==================== УТИЛИТЫ ====================
const $ = (sel) => document.querySelector(sel);
const formatPrice = (n) => n.toLocaleString('ru-RU');

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ==================== РЕНДЕР ====================
function renderServices() {
  const grid = $('#services-grid');
  grid.innerHTML = SERVICES.map((s) => `
    <article class="card">
      <h3>${escapeHtml(s.title)}</h3>
      <p>${escapeHtml(s.desc)}</p>
      <div class="price">${escapeHtml(s.price)}</div>
    </article>
  `).join('');
}

function renderTariffs() {
  const grid = $('#tariffs-grid');
  grid.innerHTML = TARIFFS.map((t) => `
    <article class="card">
      <h3>${escapeHtml(t.name)}</h3>
      <ul style="list-style:none;display:flex;flex-direction:column;gap:0.4rem;margin-bottom:1rem;">
        ${t.features.map((f) => `<li style="font-size:0.9rem;color:var(--text-muted);">• ${escapeHtml(f)}</li>`).join('')}
      </ul>
      <div class="price">${formatPrice(t.price)} ₽</div>
    </article>
  `).join('');
}

function renderCatalog(filter = 'all') {
  const grid = $('#catalog-grid');
  const items = filter === 'all' ? CATALOG : CATALOG.filter((c) => c.category === filter);
  grid.innerHTML = items.map((c) => `
    <article class="card">
      <h3>${escapeHtml(c.title)}</h3>
      <p style="font-size:0.85rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">${escapeHtml(c.category)}</p>
      <div class="price">${escapeHtml(c.price)}</div>
    </article>
  `).join('');
}

// ==================== ФИЛЬТР КАТАЛОГА ====================
function initCatalogFilter() {
  const buttons = document.querySelectorAll('.filter-btn');
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      buttons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      renderCatalog(btn.dataset.filter);
    });
  });
}

// ==================== КАЛЬКУЛЯТОР ====================
function initCalculator() {
  const typeSel = $('#calc-type');
  const weeksInp = $('#calc-weeks');
  const urgencySel = $('#calc-urgency');
  const priceEl = $('#calc-price');

  function calc() {
    const base = BASE_PRICES[typeSel.value];
    const weeks = Math.max(1, Math.min(52, parseInt(weeksInp.value, 10) || 1));
    const urgency = parseFloat(urgencySel.value) || 1;
    const total = Math.round(base * urgency);
    priceEl.textContent = formatPrice(total);
  }

  [typeSel, weeksInp, urgencySel].forEach((el) => el.addEventListener('input', calc));
  calc();
}

// ==================== МОДАЛЬНОЕ ОКНО ====================
const modal = $('#confirm-modal');
const modalTitle = $('#modal-title');
const modalText = $('#modal-text');
const modalOverlay = $('#modal-overlay');
const modalClose = $('#modal-close');
const modalOk = $('#modal-ok');

function openModal(title, text) {
  modalTitle.textContent = title;
  modalText.textContent = text;
  modal.setAttribute('aria-hidden', 'false');
}

function closeModal() {
  modal.setAttribute('aria-hidden', 'true');
}

modalClose.addEventListener('click', closeModal);
modalOk.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', closeModal);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && modal.getAttribute('aria-hidden') === 'false') closeModal();
});

// ==================== ФОРМА ОБРАТНОЙ СВЯЗИ ====================
function initContactForm() {
  const form = $('#contact-form');
  const fields = { name: $('#cf-name'), email: $('#cf-email'), message: $('#cf-message') };
  const errors = { name: $('#cf-name-error'), email: $('#cf-email-error'), message: $('#cf-message-error') };
  const msg = $('#form-msg');
  const submitBtn = $('#cf-submit');

  function clearErrors() {
    Object.values(errors).forEach((el) => (el.textContent = ''));
    msg.style.display = 'none';
  }

  function validate() {
    clearErrors();
    let valid = true;

    if (!fields.name.value.trim() || fields.name.value.trim().length < 2) {
      errors.name.textContent = 'Введите имя (минимум 2 символа)';
      valid = false;
    }
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRe.test(fields.email.value)) {
      errors.email.textContent = 'Введите корректный email';
      valid = false;
    }
    if (!fields.message.value.trim() || fields.message.value.trim().length < 10) {
      errors.message.textContent = 'Напишите сообщение (минимум 10 символов)';
      valid = false;
    }
    return valid;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validate()) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Отправляется...';

    // Мок-отправка: имитация сетевого запроса без перезагрузки страницы
    await new Promise((resolve) => setTimeout(resolve, 800));

    msg.style.display = 'block';
    msg.textContent = 'Данные приняты (режим демонстрации).';
    form.reset();
    openModal('Заявка принята', 'Спасибо! Мы свяжемся с вами в ближайшее время.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Отправить заявку';
  });
}

// ==================== МЕНЮ МОБИЛКИ ====================
function initMobileMenu() {
  const toggle = $('#nav-toggle');
  const nav = $('#main-nav');
  toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('.nav a').forEach((a) => {
    a.addEventListener('click', () => {
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// ==================== ЗАПУСК ====================
document.addEventListener('DOMContentLoaded', () => {
  renderServices();
  renderTariffs();
  renderCatalog();
  initCatalogFilter();
  initCalculator();
  initContactForm();
  initMobileMenu();
});