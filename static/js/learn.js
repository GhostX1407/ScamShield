/**
 * ScamShield — Learn Why Controller
 * Fetches educational cards from /api/learn/<lang>, provides real-time search,
 * and scrolls/highlights cards referenced via URL hash.
 */

(function () {
  'use strict';

  const learnGrid = document.getElementById('learnGrid');
  const learnSearchInput = document.getElementById('learnSearchInput');
  const learnNoResults = document.getElementById('learnNoResults');

  let cardsData = {};

  async function fetchLearnCards() {
    const lang = window.i18n ? window.i18n.getLang() : 'en';
    try {
      const resp = await fetch(`/api/learn/${lang}`);
      if (!resp.ok) throw new Error('Failed to load learn content');
      cardsData = await resp.json();
      renderCards(cardsData);
      checkHashTarget();
    } catch (err) {
      console.error(err);
      window.showToast('Could not load learn cards.', 'error');
    }
  }

  function renderCards(cards) {
    learnGrid.innerHTML = '';
    const flagIds = Object.keys(cards);

    if (flagIds.length === 0) {
      learnNoResults.style.display = 'block';
      return;
    }
    learnNoResults.style.display = 'none';

    const whatLabel = window.i18n.t('learn_card_what', 'What this is');
    const whyLabel = window.i18n.t('learn_card_why', 'Why scammers use it');
    const doLabel = window.i18n.t('learn_card_do', 'What to do now');

    flagIds.forEach((flagId) => {
      const card = cards[flagId];
      const cardEl = document.createElement('article');
      cardEl.className = 'learn-card';
      cardEl.id = flagId;
      cardEl.setAttribute('data-id', flagId);

      cardEl.innerHTML = `
        <h3 class="learn-card-title">
          <span aria-hidden="true">🛡️</span>
          <span>${window.escapeHtml(card.title || flagId)}</span>
        </h3>

        <div class="learn-subblock">
          <span class="learn-subblock-title">${window.escapeHtml(whatLabel)}</span>
          <p class="learn-subblock-body">${window.escapeHtml(card.what || '')}</p>
        </div>

        <div class="learn-subblock">
          <span class="learn-subblock-title why">${window.escapeHtml(whyLabel)}</span>
          <p class="learn-subblock-body">${window.escapeHtml(card.why || '')}</p>
        </div>

        <div class="learn-subblock">
          <span class="learn-subblock-title do">${window.escapeHtml(doLabel)}</span>
          <p class="learn-subblock-body">${window.escapeHtml(card.do || '')}</p>
        </div>
      `;

      learnGrid.appendChild(cardEl);
    });
  }

  // ── Search & Filter ─────────────────────────────────────────────────────
  function filterCards() {
    const query = learnSearchInput.value.trim().toLowerCase();
    const cards = learnGrid.querySelectorAll('.learn-card');
    let visibleCount = 0;

    cards.forEach((card) => {
      const text = card.textContent.toLowerCase();
      const matches = !query || text.includes(query);
      card.style.display = matches ? 'flex' : 'none';
      if (matches) visibleCount++;
    });

    learnNoResults.style.display = visibleCount === 0 ? 'block' : 'none';
  }

  // ── Hash Anchoring & Highlighting ───────────────────────────────────────
  function checkHashTarget() {
    const hash = window.location.hash.replace('#', '');
    if (!hash) return;

    // Small delay to ensure DOM rendering
    setTimeout(() => {
      const targetCard = document.getElementById(hash);
      if (targetCard) {
        // Clear previous highlights
        document.querySelectorAll('.learn-card.highlight-target').forEach((c) => {
          c.classList.remove('highlight-target');
        });

        targetCard.classList.add('highlight-target');
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 150);
  }

  // ── Event Bindings ──────────────────────────────────────────────────────
  function bindEvents() {
    learnSearchInput.addEventListener('input', filterCards);

    window.addEventListener('hashchange', checkHashTarget);

    document.addEventListener('scamshield:langchange', () => {
      fetchLearnCards();
    });
  }

  // Initialize
  function init() {
    bindEvents();
    fetchLearnCards();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
