/**
 * ScamShield — Scanner Controller
 * Manages tab switching, input validation, camera capture, API scanning,
 * animated result gauge rendering, text highlight mapping, and PDF export.
 */

(function () {
  'use strict';

  // ── State ───────────────────────────────────────────────────────────────
  let currentTab = 'message';
  let selectedFile = null;
  let cameraStream = null;
  let lastResult = null;
  let samplesData = null;

  // ── DOM Elements ────────────────────────────────────────────────────────
  const tabBtns = {
    message: document.getElementById('tabBtnMessage'),
    link: document.getElementById('tabBtnLink'),
    qr: document.getElementById('tabBtnQR')
  };

  const tabPanels = {
    message: document.getElementById('panelMessage'),
    link: document.getElementById('panelLink'),
    qr: document.getElementById('panelQR')
  };

  const messageInput = document.getElementById('messageInput');
  const charCounter = document.getElementById('charCounter');
  const linkInput = document.getElementById('linkInput');

  const qrDropzone = document.getElementById('qrDropzone');
  const qrFileInput = document.getElementById('qrFileInput');
  const qrPreviewContainer = document.getElementById('qrPreviewContainer');
  const qrPreviewImg = document.getElementById('qrPreviewImg');
  const qrFileName = document.getElementById('qrFileName');
  const qrFileSize = document.getElementById('qrFileSize');
  const qrRemoveBtn = document.getElementById('qrRemoveBtn');

  const cameraToggleBtn = document.getElementById('cameraToggleBtn');
  const cameraToggleIcon = document.getElementById('cameraToggleIcon');
  const cameraToggleText = document.getElementById('cameraToggleText');
  const cameraPreviewWrapper = document.getElementById('cameraPreviewWrapper');
  const cameraVideo = document.getElementById('cameraVideo');
  const cameraCanvas = document.getElementById('cameraCanvas');

  const sampleBtn = document.getElementById('sampleBtn');
  const checkBtn = document.getElementById('checkBtn');
  const checkBtnSpinner = document.getElementById('checkBtnSpinner');
  const checkBtnText = document.getElementById('checkBtnText');

  const resultSection = document.getElementById('resultSection');
  const verdictBanner = document.getElementById('verdictBanner');
  const verdictIcon = document.getElementById('verdictIcon');
  const verdictTitle = document.getElementById('verdictTitle');
  const scoreNumber = document.getElementById('scoreNumber');
  const scoreGaugeFill = document.getElementById('scoreGaugeFill');

  const upiWarningCard = document.getElementById('upiWarningCard');
  const upiPayeeVal = document.getElementById('upiPayeeVal');
  const upiNameVal = document.getElementById('upiNameVal');
  const upiAmountVal = document.getElementById('upiAmountVal');
  const upiNoteVal = document.getElementById('upiNoteVal');

  const highlightCard = document.getElementById('highlightCard');
  const highlightedTextBox = document.getElementById('highlightedTextBox');
  const flagsGrid = document.getElementById('flagsGrid');
  const linksFoundCard = document.getElementById('linksFoundCard');
  const linksFoundList = document.getElementById('linksFoundList');

  const downloadPdfBtn = document.getElementById('downloadPdfBtn');
  const checkAnotherBtn = document.getElementById('checkAnotherBtn');

  const sampleModal = document.getElementById('sampleModal');
  const sampleModalCloseBtn = document.getElementById('sampleModalCloseBtn');
  const sampleModalList = document.getElementById('sampleModalList');

  // ── Tab Management ──────────────────────────────────────────────────────
  function switchTab(tab) {
    currentTab = tab;
    Object.keys(tabBtns).forEach((key) => {
      const isActive = key === tab;
      tabBtns[key].classList.toggle('active', isActive);
      tabBtns[key].setAttribute('aria-selected', isActive);
      tabPanels[key].classList.toggle('active', isActive);
    });

    // Stop camera if user switches away from QR tab
    if (tab !== 'qr' && cameraStream) {
      stopCamera();
    }
  }

  // ── Character Counter ───────────────────────────────────────────────────
  function updateCharCount() {
    if (!messageInput || !charCounter) return;
    const len = messageInput.value.length;
    charCounter.textContent = `${len.toLocaleString()} / 10,000`;
    charCounter.classList.toggle('limit-near', len > 9000 && len <= 10000);
    charCounter.classList.toggle('limit-reached', len >= 10000);
  }

  // ── QR File Handling ────────────────────────────────────────────────────
  function setFile(file) {
    if (!file) {
      selectedFile = null;
      qrPreviewContainer.style.display = 'none';
      qrDropzone.style.display = 'block';
      qrFileInput.value = '';
      return;
    }

    // Size limit: 5 MB
    if (file.size > 5 * 1024 * 1024) {
      window.showToast(window.i18n.t('err_file_too_large', 'File too large (> 5 MB)'), 'error');
      return;
    }

    selectedFile = file;
    qrFileName.textContent = file.name;
    qrFileSize.textContent = formatBytes(file.size);

    const reader = new FileReader();
    reader.onload = (e) => {
      qrPreviewImg.src = e.target.result;
      qrPreviewContainer.style.display = 'flex';
      qrDropzone.style.display = 'none';
    };
    reader.readAsDataURL(file);
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  // ── Camera Scanner ──────────────────────────────────────────────────────
  async function toggleCamera() {
    if (cameraStream) {
      stopCamera();
    } else {
      await startCamera();
    }
  }

  async function startCamera() {
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      cameraVideo.srcObject = cameraStream;
      await cameraVideo.play();

      cameraPreviewWrapper.style.display = 'block';
      cameraToggleText.textContent = 'Stop Camera';
      cameraToggleIcon.textContent = '⏹️';

      // Scan video frames
      scanVideoFrame();
    } catch (err) {
      console.warn('Camera access denied or unavailable:', err);
      window.showToast('Unable to access camera. Please upload an image instead.', 'warning');
      stopCamera();
    }
  }

  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop());
      cameraStream = null;
    }
    if (cameraVideo) {
      cameraVideo.srcObject = null;
    }
    cameraPreviewWrapper.style.display = 'none';
    cameraToggleText.textContent = 'Scan with Camera';
    cameraToggleIcon.textContent = '📹';
  }

  function scanVideoFrame() {
    if (!cameraStream) return;
    if (cameraVideo.readyState === cameraVideo.HAVE_ENOUGH_DATA) {
      cameraCanvas.width = cameraVideo.videoWidth;
      cameraCanvas.height = cameraVideo.videoHeight;
      const ctx = cameraCanvas.getContext('2d');
      ctx.drawImage(cameraVideo, 0, 0, cameraCanvas.width, cameraCanvas.height);

      // Attempt snapshot capture after user stabilizes
      cameraCanvas.toBlob((blob) => {
        if (blob && cameraStream) {
          // If camera is active, we can auto capture or let user click Check Now
        }
      }, 'image/jpeg', 0.85);
    }
    requestAnimationFrame(scanVideoFrame);
  }

  // ── Samples Modal ───────────────────────────────────────────────────────
  async function loadSamples() {
    if (samplesData) return samplesData;
    try {
      const resp = await fetch('/api/samples');
      if (resp.ok) {
        samplesData = await resp.json();
        return samplesData;
      }
    } catch (e) {
      console.error('Failed to load samples:', e);
    }
    return [];
  }

  async function openSampleModal() {
    const samples = await loadSamples();
    sampleModalList.innerHTML = '';

    if (!samples || samples.length === 0) {
      sampleModalList.innerHTML = '<p style="color: var(--text-muted); text-align: center;">No samples available.</p>';
    } else {
      samples.forEach((sample) => {
        const itemBtn = document.createElement('button');
        itemBtn.type = 'button';
        itemBtn.className = 'sample-item-btn';
        itemBtn.innerHTML = `
          <span class="sample-item-label">${window.escapeHtml(sample.label)}</span>
          <span class="sample-item-snippet">${window.escapeHtml(sample.text)}</span>
        `;
        itemBtn.addEventListener('click', () => {
          selectSample(sample);
          window.closeModal('sampleModal');
        });
        sampleModalList.appendChild(itemBtn);
      });
    }

    window.openModal('sampleModal');
  }

  function selectSample(sample) {
    if (sample.type === 'link') {
      switchTab('link');
      linkInput.value = sample.text;
    } else {
      switchTab('message');
      messageInput.value = sample.text;
      updateCharCount();
    }
    // Auto-trigger scan
    handleCheck();
  }

  // ── Analysis / Check ────────────────────────────────────────────────────
  function setLoading(loading) {
    checkBtn.disabled = loading;
    checkBtnSpinner.style.display = loading ? 'inline-block' : 'none';
    checkBtnText.textContent = loading
      ? window.i18n.t('scan_checking', 'Checking…')
      : window.i18n.t('scan_btn_check', 'Check Now');
  }

  async function handleCheck() {
    let payloadType = currentTab;

    if (payloadType === 'message') {
      const text = messageInput.value.trim();
      if (!text) {
        window.showToast(window.i18n.t('err_empty', 'Please enter some text before checking.'), 'warning');
        messageInput.focus();
        return;
      }
      await scanTextPayload(text);
    } else if (payloadType === 'link') {
      const link = linkInput.value.trim();
      if (!link) {
        window.showToast(window.i18n.t('err_empty', 'Please enter some text before checking.'), 'warning');
        linkInput.focus();
        return;
      }
      await scanTextPayload(link);
    } else if (payloadType === 'qr') {
      if (cameraStream) {
        // Capture frame from camera canvas
        cameraCanvas.toBlob(async (blob) => {
          if (blob) {
            stopCamera();
            const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
            await scanImagePayload(file);
          }
        }, 'image/jpeg', 0.9);
      } else if (selectedFile) {
        await scanImagePayload(selectedFile);
      } else {
        window.showToast(window.i18n.t('err_no_file', 'Please choose an image file.'), 'warning');
      }
    }
  }

  async function scanTextPayload(text) {
    setLoading(true);
    try {
      const resp = await fetch('/api/scan/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || 'Server error occurred');
      }
      renderResult(data);
    } catch (err) {
      window.showToast(err.message || window.i18n.t('err_server', 'Something went wrong.'), 'error');
    } finally {
      setLoading(false);
    }
  }

  async function scanImagePayload(file) {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('image', file);

      const resp = await fetch('/api/scan/image', {
        method: 'POST',
        body: formData
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || 'Server error occurred');
      }
      renderResult(data);
    } catch (err) {
      window.showToast(err.message || window.i18n.t('err_server', 'Something went wrong.'), 'error');
    } finally {
      setLoading(false);
    }
  }

  // ── Render Result ───────────────────────────────────────────────────────
  function renderResult(result) {
    lastResult = result;

    const verdict = result.verdict || 'safe';
    const score = Number.isInteger(result.score) ? result.score : 0;

    // 1. Verdict Banner
    verdictBanner.className = `verdict-banner verdict-${verdict}`;
    verdictTitle.textContent = window.i18n.t(`result_verdict_${verdict}`, formatVerdictText(verdict));

    if (verdict === 'safe') {
      verdictIcon.textContent = '🛡️';
      scoreGaugeFill.style.stroke = 'var(--safe-color)';
    } else if (verdict === 'suspicious') {
      verdictIcon.textContent = '⚠️';
      scoreGaugeFill.style.stroke = 'var(--suspicious-color)';
    } else {
      verdictIcon.textContent = '🚨';
      scoreGaugeFill.style.stroke = 'var(--dangerous-color)';
    }

    // 2. Score Meter Animation
    animateScoreCounter(score);
    const strokeDash = 220 - (220 * Math.min(100, Math.max(0, score))) / 100;
    scoreGaugeFill.style.strokeDashoffset = strokeDash;

    // 3. UPI Warning Card
    if (result.type === 'upi' && result.upi_details) {
      const upi = result.upi_details;
      upiPayeeVal.textContent = upi.vpa || '—';
      upiNameVal.textContent = upi.name || '—';
      upiAmountVal.textContent = upi.amount ? `₹${upi.amount}` : 'Not fixed (Any amount)';
      upiNoteVal.textContent = upi.note || '—';
      upiWarningCard.classList.add('active');
    } else {
      upiWarningCard.classList.remove('active');
    }

    // 4. Highlighted Text
    const rawText = result.raw_text || result.decoded_text || messageInput.value || linkInput.value || '';
    if (rawText && result.highlights && result.highlights.length > 0) {
      highlightedTextBox.innerHTML = buildHighlightedMarkup(rawText, result.highlights);
      highlightCard.style.display = 'block';
    } else if (rawText) {
      highlightedTextBox.textContent = rawText;
      highlightCard.style.display = 'block';
    } else {
      highlightCard.style.display = 'none';
    }

    // 5. Red Flags Grid
    renderFlags(result.flags || []);

    // 6. Links found
    if (result.urls && result.urls.length > 0) {
      linksFoundList.innerHTML = '';
      result.urls.forEach((urlInfo) => {
        const item = document.createElement('div');
        item.style.padding = '0.75rem 1rem';
        item.style.background = 'rgba(0,0,0,0.3)';
        item.style.borderRadius = 'var(--radius-md)';
        item.style.border = '1px solid var(--border-subtle)';
        item.innerHTML = `
          <div style="font-family: var(--font-mono); font-size: 0.9rem; word-break: break-all; color: var(--cyan-primary);">
            ${window.escapeHtml(urlInfo.url || urlInfo)}
          </div>
          ${urlInfo.domain ? `<div style="font-size: 0.78rem; color: var(--text-subtle); margin-top: 0.2rem;">Domain: ${window.escapeHtml(urlInfo.domain)}</div>` : ''}
        `;
        linksFoundList.appendChild(item);
      });
      linksFoundCard.style.display = 'block';
    } else {
      linksFoundCard.style.display = 'none';
    }

    // Show section with smooth scroll
    resultSection.classList.add('active');
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function formatVerdictText(verdict) {
    if (verdict === 'safe') return 'Looks Safe';
    if (verdict === 'suspicious') return 'Looks Suspicious';
    if (verdict === 'dangerous') return 'This is Dangerous';
    return verdict;
  }

  function animateScoreCounter(target) {
    let current = 0;
    const duration = 600;
    const stepTime = 15;
    const increment = target / (duration / stepTime);

    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        scoreNumber.textContent = target;
        clearInterval(timer);
      } else {
        scoreNumber.textContent = Math.round(current);
      }
    }, stepTime);
  }

  function buildHighlightedMarkup(text, highlights) {
    if (!highlights || highlights.length === 0) {
      return window.escapeHtml(text);
    }

    // Sort spans ascending by start
    const sorted = [...highlights].sort((a, b) => a.start - b.start);

    let html = '';
    let lastIdx = 0;

    for (const h of sorted) {
      if (h.start < lastIdx) continue; // Skip overlaps
      // Append preceding safe text
      html += window.escapeHtml(text.substring(lastIdx, h.start));

      // Append highlighted word
      const wordText = window.escapeHtml(text.substring(h.start, h.end));
      const catClass = `hl-${h.category || 'urgency'}`;
      html += `<mark class="hl-tag ${catClass}" title="${window.escapeHtml(h.category || '')}">${wordText}</mark>`;
      lastIdx = h.end;
    }

    if (lastIdx < text.length) {
      html += window.escapeHtml(text.substring(lastIdx));
    }

    return html;
  }

  function renderFlags(flags) {
    flagsGrid.innerHTML = '';
    if (!flags || flags.length === 0) {
      flagsGrid.innerHTML = `
        <div class="empty-flags-state" style="grid-column: 1 / -1;">
          <span class="empty-flags-icon" aria-hidden="true">✅</span>
          <p data-i18n="result_no_flags">${window.i18n.t('result_no_flags', 'No red flags found.')}</p>
        </div>
      `;
      return;
    }

    flags.forEach((flag) => {
      const card = document.createElement('div');
      card.className = 'flag-item-card';

      const flagId = flag.id || '';
      const title = flag.title || flag.id || 'Warning';
      const severity = (flag.severity || 'medium').toLowerCase();
      const desc = flag.description || flag.message || '';

      card.innerHTML = `
        <div class="flag-header">
          <div class="flag-title-wrap">
            <span class="flag-icon" aria-hidden="true">🚩</span>
            <h4 class="flag-title">${window.escapeHtml(title)}</h4>
          </div>
          <span class="severity-badge severity-${severity}">${severity}</span>
        </div>
        <p class="flag-description">${window.escapeHtml(desc)}</p>
        <a href="/learn#${encodeURIComponent(flagId)}" class="flag-action-link">
          <span data-i18n="result_learn_why">${window.i18n.t('result_learn_why', 'Learn Why')}</span>
          <span aria-hidden="true">→</span>
        </a>
      `;

      flagsGrid.appendChild(card);
    });
  }

  // ── PDF Export ──────────────────────────────────────────────────────────
  async function downloadPdf() {
    if (!lastResult) return;

    downloadPdfBtn.disabled = true;
    const originalText = downloadPdfBtn.innerHTML;
    downloadPdfBtn.innerHTML = '<span class="spinner" style="border-top-color: #fff;"></span> Preparing PDF…';

    try {
      const lang = window.i18n.getLang() || 'en';
      const resp = await fetch('/api/export/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang, result: lastResult })
      });

      if (!resp.ok) {
        throw new Error('PDF export failed');
      }

      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `scamshield_report_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      window.showToast('Report downloaded successfully!', 'success');
    } catch (err) {
      window.showToast('Failed to download PDF report.', 'error');
    } finally {
      downloadPdfBtn.disabled = false;
      downloadPdfBtn.innerHTML = originalText;
    }
  }

  // ── Reset for Another Scan ──────────────────────────────────────────────
  function resetScanner() {
    messageInput.value = '';
    linkInput.value = '';
    setFile(null);
    updateCharCount();

    if (cameraStream) {
      stopCamera();
    }

    resultSection.classList.remove('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Event Bindings ──────────────────────────────────────────────────────
  function bindEvents() {
    // Tab switching
    Object.keys(tabBtns).forEach((tab) => {
      tabBtns[tab].addEventListener('click', () => switchTab(tab));
    });

    // Character counter
    messageInput.addEventListener('input', updateCharCount);

    // QR Drag and Drop
    qrDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      qrDropzone.classList.add('drag-over');
    });

    qrDropzone.addEventListener('dragleave', () => {
      qrDropzone.classList.remove('drag-over');
    });

    qrDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      qrDropzone.classList.remove('drag-over');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        setFile(e.dataTransfer.files[0]);
      }
    });

    qrFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        setFile(e.target.files[0]);
      }
    });

    qrRemoveBtn.addEventListener('click', () => setFile(null));

    // Camera toggle
    cameraToggleBtn.addEventListener('click', toggleCamera);

    // Sample Picker
    sampleBtn.addEventListener('click', openSampleModal);
    sampleModalCloseBtn.addEventListener('click', () => window.closeModal('sampleModal'));
    sampleModal.addEventListener('click', (e) => {
      if (e.target === sampleModal) window.closeModal('sampleModal');
    });

    // Run Scan
    checkBtn.addEventListener('click', handleCheck);

    // Actions
    downloadPdfBtn.addEventListener('click', downloadPdf);
    checkAnotherBtn.addEventListener('click', resetScanner);

    // Re-render language-dependent items on language switch
    document.addEventListener('scamshield:langchange', () => {
      if (lastResult) {
        const verdict = lastResult.verdict || 'safe';
        verdictTitle.textContent = window.i18n.t(`result_verdict_${verdict}`, formatVerdictText(verdict));
      }
    });
  }

  // Initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindEvents);
  } else {
    bindEvents();
  }
})();
