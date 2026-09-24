/**
 * ScamShield — i18n Translation Engine
 * Handles dynamic English/Hindi language toggling, label substitution,
 * and custom events for page-specific component re-rendering.
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'scamshield_lang';
  const SUPPORTED_LANGS = ['en', 'hi'];
  const cache = { en: null, hi: null };

  let currentLang = localStorage.getItem(STORAGE_KEY) || 'en';
  if (!SUPPORTED_LANGS.includes(currentLang)) {
    currentLang = 'en';
  }

  /**
   * Fetch dictionary for given language from API or return cached
   */
  async function getTranslations(lang) {
    if (cache[lang]) {
      return cache[lang];
    }
    try {
      const resp = await fetch(`/api/i18n/${lang}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      cache[lang] = data;
      return data;
    } catch (err) {
      console.error(`[i18n] Failed to fetch translations for '${lang}':`, err);
      return {};
    }
  }

  /**
   * Look up a key in current language
   */
  function t(key, fallback = '') {
    const dict = cache[currentLang] || {};
    return dict[key] !== undefined ? dict[key] : (fallback || key);
  }

  /**
   * Translate all DOM nodes with data-i18n attributes
   */
  async function applyTranslations(lang) {
    currentLang = lang;
    localStorage.setItem(STORAGE_KEY, lang);

    document.documentElement.lang = lang;
    document.documentElement.setAttribute('data-lang', lang);

    const dict = await getTranslations(lang);

    // Update data-i18n text content
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      if (dict[key] !== undefined) {
        if (el.tagName === 'INPUT' && (el.type === 'button' || el.type === 'submit')) {
          el.value = dict[key];
        } else {
          el.textContent = dict[key];
        }
      }
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key] !== undefined) {
        el.placeholder = dict[key];
      }
    });

    // Update title tooltips
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      const key = el.getAttribute('data-i18n-title');
      if (dict[key] !== undefined) {
        el.title = dict[key];
      }
    });

    // Toggle button label
    const toggleBtnText = document.getElementById('langToggleText');
    if (toggleBtnText) {
      toggleBtnText.textContent = lang === 'en' ? 'हिन्दी' : 'English';
    }

    // Broadcast change to other scripts
    document.dispatchEvent(new CustomEvent('scamshield:langchange', { detail: { lang, dict } }));
  }

  /**
   * Initialize on DOM ready
   */
  async function init() {
    await applyTranslations(currentLang);

    const toggleBtn = document.getElementById('langToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', async () => {
        const nextLang = currentLang === 'en' ? 'hi' : 'en';
        await applyTranslations(nextLang);
      });
    }
  }

  // Expose global helpers
  window.i18n = {
    getLang: () => currentLang,
    t,
    applyTranslations,
    getTranslations
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
