/* ═══════════════════════════════════════════════════════════════════
   AquaLens — landing.js
   Scripts for index.html (Landing Page)
   Depends on: shared.js
═══════════════════════════════════════════════════════════════════ */

'use strict';

// ── Navbar scroll effect ────────────────────────────────────────────
(function initNav() {
  const nav = document.querySelector('.navbar') || document.querySelector('nav');
  if (!nav) return;
  window.addEventListener('scroll', AQ.debounce(() => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  }, 50));
})();

// ── Particle / Floating dots canvas ────────────────────────────────
(function initParticles() {
  const canvas = document.getElementById('particles');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', AQ.debounce(resize, 200));

  function mkParticle() {
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.25,
      vy: -Math.random() * 0.4 - 0.1,
      alpha: Math.random() * 0.5 + 0.1,
    };
  }

  for (let i = 0; i < 80; i++) particles.push(mkParticle());

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,201,167,${p.alpha})`;
      ctx.fill();

      p.x += p.vx;
      p.y += p.vy;
      p.alpha -= 0.0005;

      if (p.y < -5 || p.alpha <= 0) Object.assign(p, mkParticle(), { y: H + 5 });
    });
    requestAnimationFrame(draw);
  }
  draw();
})();

// ── Stats counter animation (triggered on scroll) ───────────────────
(function initStats() {
  const statEls = document.querySelectorAll('[data-count]');
  if (!statEls.length) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el     = entry.target;
        const target = parseFloat(el.dataset.count);
        const suffix = el.dataset.suffix || '';
        AQ.animateCounter(el, target, 1400, suffix);
        obs.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  statEls.forEach(el => obs.observe(el));
})();

// ── Scroll reveal cards ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  AQ.initScrollReveal('[data-reveal]');
});

// ── Typewriter effect for hero text ────────────────────────────────
function typewriter(el, texts, speed = 55, pause = 2200) {
  if (!el) return;
  let ti = 0, ci = 0, deleting = false;

  function tick() {
    const current = texts[ti];
    if (!deleting) {
      el.textContent = current.slice(0, ++ci);
      if (ci === current.length) {
        deleting = true;
        setTimeout(tick, pause);
        return;
      }
    } else {
      el.textContent = current.slice(0, --ci);
      if (ci === 0) {
        deleting = false;
        ti = (ti + 1) % texts.length;
      }
    }
    setTimeout(tick, deleting ? speed * 0.6 : speed);
  }
  tick();
}

// Activate typewriter if element exists
document.addEventListener('DOMContentLoaded', () => {
  const tw = document.getElementById('typewriter-text');
  if (tw) {
    typewriter(tw, [
      'كشف المياه الجوفية',
      'تحليل الطبقات المائية',
      'تقدير عمق الحفر',
      'رسم خرائط GRACE-FO',
    ]);
  }
});

// ── Mobile menu toggle ──────────────────────────────────────────────
window.toggleMobileMenu = function () {
  const menu = document.getElementById('mobileMenu');
  if (menu) menu.classList.toggle('open');
};

// ── Smooth anchor scrolling ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
});
