'use strict';

// ==================== КОНФИГУРАЦИЯ И МОК-ДАННЫЕ ====================
const STORAGE_KEY = 'crm_demo_records_v1';

const FIELD_LABELS = {
  id: 'ID',
  title: 'Название',
  status: 'Статус',
  date: 'Дата',
  amount: 'Сумма'
};

const STATUSES = [
  { value: 'new', label: 'Новая', badge: 'badge-new' },
  { value: 'inprogress', label: 'В работе', badge: 'badge-inprogress' },
  { value: 'done', label: 'Завершена', badge: 'badge-done' },
  { value: 'cancelled', label: 'Отменена', badge: 'badge-cancelled' }
];

let records = [
  { id: 101, title: 'Разработка лендинга', status: 'done', date: '2026-01-15', amount: 45000 },
  { id: 102, title: 'Корпоративный портал', status: 'inprogress', date: '2026-02-03', amount: 120000 },
  { id: 103, title: 'Интернет-магазин', status: 'new', date: '2026-02-10', amount: 300000 },
  { id: 104, title: 'SEO-аудит сайта', status: 'cancelled', date: '2026-01-28', amount: 35000 },
  { id: 105, title: 'Мобильное приложение', status: 'new', date: '2026-03-01', amount: 250000 },
  { id: 106, title: 'Дизайн брендбука', status: 'done', date: '2026-02-20', amount: 55000 },
  { id: 107, title: 'Настройка контекста', status: 'inprogress', date: '2026-03-05', amount: 40000 },
  { id: 108, title: 'SMM-стратегия', status: 'new', date: '2026-03-08', amount: 30000 }
];

// ==================== УТИЛИТЫ ====================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const escapeHtml = (text) => {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};
const formatDate = (iso) => iso ? iso.slice(0, 10).replace(/-/g, '.') : '';
const formatAmount = (n) => Number(n).toLocaleString('ru-RU', { minimumFractionDigits: 2 }) + ' ₽';
const nextId = () => Math.max(0, ...records.map((r) => r.id), 0) + 1;

// ==================== LOCALSTORAGE ====================
function loadRecords() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) records = JSON.parse(raw);
  } catch (e) {}
}
function saveRecords() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
  } catch (e) {}
}

// ==================== ФИЛЬТРЫ / СОРТИРОВКА ====================
let filterState = {
  search: '',
  status: '',
  dateFrom: '',
  sortField: 'id',
  sortDir: 'desc'
};

function filteredRecords() {
  return records.filter((r) => {
    const search = filterState.search.toLowerCase();
    const matchSearch =
      String(r.id).toLowerCase().includes(search) ||
      r.title.toLowerCase().includes(search) ||
      String(r.amount).includes(search);
    const matchStatus = filterState.status ? r.status === filterState.status : true;
    const matchDate = filterState.dateFrom ? r.date >= filterState.dateFrom : true;
    return matchSearch && matchStatus && matchDate;
  }).sort((a, b) => {
    let av = a[filterState.sortField];
    let bv = b[filterState.sortField];
    if (filterState.sortField === 'amount') { av = Number(av); bv = Number(bv); }
    if (filterState.sortField === 'date') { av = String(av); bv = String(bv); }
    if (av < bv) return filterState.sortDir === 'asc' ? -1 : 1;
    if (av > bv) return filterState.sortDir === 'asc' ? 1 : -1;
    return 0;
  });
}

// ==================== РЕНДЕР МЕТРИК ====================
function renderMetrics() {
  const grid = $('#metrics-grid');
  const total = records.length;
  const done = records.filter((r) => r.status === 'done').length;
  const inProgress = records.filter((r) => r.status === 'inprogress').length;
  const totalSum = records.reduce((sum, r) => sum + Number(r.amount), 0);

  const cards = [
    { value: total, label: 'Всего записей', delta: '', deltaClass: '' },
    { value: done, label: 'Завершено', delta: '', deltaClass: '' },
    { value: inProgress, label: 'В работе', delta: '', deltaClass: '' },
    { value: formatAmount(totalSum), label: 'Общая сумма', delta: '', deltaClass: '' }
  ];

  grid.innerHTML = cards.map((c) => `
    <div class="metric-card">
      <div class="metric-value">${escapeHtml(c.value)}</div>
      <div class="metric-label">${escapeHtml(c.label)}</div>
      ${c.delta ? `<div class="metric-delta ${c.deltaClass}">${escapeHtml(c.delta)}</div>` : ''}
    </div>
  `).join('');
}

// ==================== РЕНДЕР ТАБЛИЦЫ ====================
function renderTable() {
  const tbody = $('#records-tbody');
  const emptyMsg = $('#empty-msg');
  const items = filteredRecords();

  if (!items.length) {
    tbody.innerHTML = '';
    emptyMsg.style.display = 'block';
    return;
  }
  emptyMsg.style.display = 'none';

  tbody.innerHTML = items.map((r) => {
    const stat = STATUSES.find((s) => s.value === r.status) || STATUSES[0];
    return `
      <tr data-id="${escapeHtml(r.id)}">
        <td>${escapeHtml(r.id)}</td>
        <td>${escapeHtml(r.title)}</td>
        <td><span class="badge ${escapeHtml(stat.badge)}">${escapeHtml(stat.label)}</span></td>
        <td>${formatDate(r.date)}</td>
        <td>${formatAmount(r.amount)}</td>
        <td class="actions">
          <button type="button" class="btn-edit" data-id="${escapeHtml(r.id)}" title="Изменить статус">Статус</button>
          <button type="button" class="btn-delete" data-id="${escapeHtml(r.id)}" title="Удалить запись">Удалить</button>
        </td>
      </tr>
    `;
  }).join('');

  // события на кнопки действий
  tbody.querySelectorAll('.btn-edit').forEach((btn) => {
    btn.addEventListener('click', () => changeStatus(btn.dataset.id));
  });
  tbody.querySelectorAll('.btn-delete').forEach((btn) => {
    btn.addEventListener('click', () => deleteRecord(btn.dataset.id));
  });
}

// ==================== ПЕРЕСЧЁТ МЕТРИК ПРИ ИЗМЕНЕНИИ ====================
function refresh() {
  renderMetrics();
  renderTable();
  renderStatusFilter();
}

// ==================== ФИЛЬТР ПО СТАТУСУ ====================
function renderStatusFilter() {
  const sel = $('#inp-status');
  const used = [...new Set(records.map((r) => r.status))];
  const html = ['<option value="">Все статусы</option>']
    .concat(STATUSES.filter((s) => used.includes(s.value)).map((s) =>
      `<option value="${escapeHtml(s.value)}">${escapeHtml(s.label)}</option>`
    )).join('');
  sel.innerHTML = html;
  sel.value = filterState.status;
}

// ==================== ПОИСК ====================
function initSearch() {
  const inp = $('#inp-search');
  inp.addEventListener('input', (e) => {
    filterState.search = e.target.value;
    refresh();
  });
}

// ==================== ФИЛЬТР ПО СТАТУСУ ====================
function initStatusFilter() {
  const sel = $('#inp-status');
  sel.addEventListener('change', (e) => {
    filterState.status = e.target.value;
    refresh();
  });
}

// ==================== ФИЛЬТР ПО ДАТЕ ====================
function initDateFilter() {
  const inp = $('#inp-date');
  inp.addEventListener('change', (e) => {
    filterState.dateFrom = e.target.value;
    refresh();
  });
}

// ==================== СОРТИРОВКА ПО КОЛОНКАМ ====================
function initSort() {
  $('#records-table').querySelectorAll('th[data-sort]').forEach((th) => {
    th.addEventListener('click', () => {
      const field = th.dataset.sort;
      if (filterState.sortField === field) {
        filterState.sortDir = filterState.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        filterState.sortField = field;
        filterState.sortDir = 'asc';
      }
      refresh();
      renderSortHints();
    });
  });
}

function renderSortHints() {
  $('#records-table').querySelectorAll('th[data-sort]').forEach((th) => {
    const hint = th.querySelector('.sort-hint');
    if (th.dataset.sort === filterState.sortField) {
      hint.textContent = filterState.sortDir === 'asc' ? ' ▲' : ' ▼';
    } else {
      hint.textContent = '';
    }
  });
}

// ==================== ДОБАВЛЕНИЕ ЗАПИСИ (МОДАЛКА) ====================
const addModal = $('#add-modal');
const modalOverlay = $('#modal-overlay');
const modalClose = $('#modal-close');
const addForm = $('#add-form');
const btnAdd = $('#btn-add');
const btnCancel = $('#btn-modal-cancel');

function openAddModal() {
  addModal.setAttribute('aria-hidden', 'false');
  $('#mf-title').focus();
}
function closeAddModal() {
  addModal.setAttribute('aria-hidden', 'true');
}

function fillStatusSelect() {
  const sel = $('#mf-status');
  sel.innerHTML = ['<option value="">Выберите статус</option>']
    .concat(STATUSES.map((s) => `<option value="${escapeHtml(s.value)}">${escapeHtml(s.label)}</option>`)).join('');
}

function initAddForm() {
  fillStatusSelect();

  btnAdd.addEventListener('click', openAddModal);
  modalClose.addEventListener('click', closeAddModal);
  modalOverlay.addEventListener('click', closeAddModal);
  btnCancel.addEventListener('click', closeAddModal);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && addModal.getAttribute('aria-hidden') === 'false') closeAddModal();
  });

  addForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const title = $('#mf-title').value.trim();
    const status = $('#mf-status').value;
    const date = $('#mf-date').value;
    const amount = $('#mf-amount').value;

    // валидация
    let ok = true;
    if (!title || title.length < 2) { showError('mf-title-error', 'Название минимум 2 символа'); ok = false; }
    if (!status) { showError('mf-status-error', 'Выберите статус'); ok = false; }
    if (!date) { showError('mf-date-error', 'Выберите дату'); ok = false; }
    if (!amount || Number(amount) < 0) { showError('mf-amount-error', 'Введите сумму ≥ 0'); ok = false; }
    if (!ok) return;

    const record = {
      id: nextId(),
      title,
      status,
      date,
      amount: Number(amount)
    };
    records.push(record);
    saveRecords();
    refresh();
    addForm.reset();
    closeAddModal();
  });
}

function showError(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
}

// ==================== ИЗМЕНЕНИЕ СТАТУСА ====================
function changeStatus(id) {
  const record = records.find((r) => r.id == id);
  if (!record) return;
  const idx = STATUSES.findIndex((s) => s.value === record.status);
  const next = STATUSES[(idx + 1) % STATUSES.length];
  record.status = next.value;
  saveRecords();
  refresh();
}

// ==================== УДАЛЕНИЕ ЗАПИСИ ====================
function deleteRecord(id) {
  if (!confirm('Удалить запись №' + id + '?')) return;
  records = records.filter((r) => r.id != id);
  saveRecords();
  refresh();
}

// ==================== ЭКСПОРТ В CSV (UTF-8 с BOM) ====================
function initExport() {
  $('#btn-export').addEventListener('click', () => {
    const items = filteredRecords();
    if (!items.length) {
      alert('Нет записей для экспорта.');
      return;
    }
    const headers = ['ID', 'Название', 'Статус', 'Дата', 'Сумма'];
    const rows = items.map((r) => {
      const stat = STATUSES.find((s) => s.value === r.status) || STATUSES[0];
      return [
        r.id,
        '"' + escapeHtml(r.title).replace(/"/g, '""') + '"',
        stat.label,
        formatDate(r.date),
        r.amount
      ].join(',');
    });
    const csv = '\uFEFF' + headers.join(',') + '\n' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'export.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

// ==================== ЗАПУСК ====================
document.addEventListener('DOMContentLoaded', () => {
  loadRecords();
  renderMetrics();
  renderStatusFilter();
  renderTable();
  initSearch();
  initStatusFilter();
  initDateFilter();
  initSort();
  initAddForm();
  initExport();
});