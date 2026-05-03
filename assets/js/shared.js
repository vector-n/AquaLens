/* ═══════════════════════════════════════════════════════════════════
   AquaLens — shared.js
   Shared utilities used by both landing and dashboard pages
═══════════════════════════════════════════════════════════════════ */

'use strict';

// ── Custom Cursor ───────────────────────────────────────────────────
(function initCursor() {
  const isTouchDevice = () => window.matchMedia('(hover: none)').matches;
  if (isTouchDevice()) return;

  const cursor = Object.assign(document.createElement('div'), {
    className: 'custom-cursor'
  });
  Object.assign(cursor.style, {
    position: 'fixed', top: 0, left: 0,
    width: '20px', height: '20px',
    border: '1.5px solid rgba(0,201,167,0.7)',
    borderRadius: '50%', pointerEvents: 'none',
    zIndex: 9999, transition: 'transform 0.15s ease, opacity 0.2s',
    transform: 'translate(-50%,-50%)'
  });
  document.body.appendChild(cursor);

  let mx = 0, my = 0;
  document.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    cursor.style.left = mx + 'px';
    cursor.style.top  = my + 'px';
  });

  document.addEventListener('mousedown', () => {
    cursor.style.transform = 'translate(-50%,-50%) scale(0.6)';
    cursor.style.borderColor = 'rgba(0,201,167,1)';
  });
  document.addEventListener('mouseup', () => {
    cursor.style.transform = 'translate(-50%,-50%) scale(1)';
    cursor.style.borderColor = 'rgba(0,201,167,0.7)';
  });
})();

// ── Scroll Reveal ───────────────────────────────────────────────────
function initScrollReveal(selector = '[data-reveal]') {
  const els = document.querySelectorAll(selector);
  if (!els.length) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  els.forEach(el => obs.observe(el));
}

// ── Number Counter Animation ────────────────────────────────────────
function animateCounter(el, target, duration = 1200, suffix = '') {
  if (!el) return;
  const start = performance.now();
  const from  = 0;

  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(from + (target - from) * ease) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Toast Notification ──────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  const existing = document.getElementById('aq-toast');
  if (existing) existing.remove();

  const colors = {
    info:    { bg: 'rgba(14,165,233,0.12)', border: 'rgba(14,165,233,0.3)',  text: '#7dd3fc' },
    success: { bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.3)',   text: '#86efac' },
    warning: { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)',  text: '#fcd34d' },
    error:   { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.3)',   text: '#fca5a5' },
  };
  const c = colors[type] || colors.info;

  const toast = document.createElement('div');
  toast.id = 'aq-toast';
  toast.textContent = message;
  Object.assign(toast.style, {
    position: 'fixed', bottom: '80px', left: '50%',
    transform: 'translateX(-50%) translateY(20px)',
    background: c.bg, border: `1px solid ${c.border}`,
    color: c.text, padding: '0.6rem 1.2rem',
    borderRadius: '8px', fontSize: '0.82rem',
    fontFamily: "'Tajawal', sans-serif",
    backdropFilter: 'blur(12px)',
    zIndex: 9999, opacity: '0',
    transition: 'all 0.3s ease',
    whiteSpace: 'nowrap', pointerEvents: 'none',
    boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
  });
  document.body.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(-50%) translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ── Copy to Clipboard ───────────────────────────────────────────────
function copyToClipboard(text, successMsg = 'تم النسخ ✓') {
  navigator.clipboard.writeText(text)
    .then(() => showToast(successMsg, 'success'))
    .catch(() => showToast('فشل النسخ', 'error'));
}

// ── Format Numbers in Arabic ────────────────────────────────────────
const AR_DIGITS = ['٠','١','٢','٣','٤','٥','٦','٧','٨','٩'];
function toArabicNumerals(n) {
  return String(n).replace(/\d/g, d => AR_DIGITS[+d]);
}

// ── Device Helpers ──────────────────────────────────────────────────
const Device = {
  isMobile:  () => window.innerWidth <= 768,
  isTablet:  () => window.innerWidth > 768 && window.innerWidth <= 1024,
  isDesktop: () => window.innerWidth > 1024,
  isTouch:   () => ('ontouchstart' in window) || navigator.maxTouchPoints > 0,
};

// ── Debounce ─────────────────────────────────────────────────────────
function debounce(fn, delay = 150) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ── Export ───────────────────────────────────────────────────────────
window.AQ = {
  showToast,
  copyToClipboard,
  toArabicNumerals,
  animateCounter,
  initScrollReveal,
  Device,
  debounce,
};
