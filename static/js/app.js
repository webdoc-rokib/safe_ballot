document.addEventListener('DOMContentLoaded', function () {
  // simple fade-in for cards
  document.querySelectorAll('.card').forEach((el, i) => {
    el.style.opacity = 0;
    el.style.transform = 'translateY(6px)';
    const delay = Math.min(20 * i, 240); // keep total stagger short
    setTimeout(() => {
      el.style.transition = 'opacity 240ms ease, transform 240ms ease';
      el.style.opacity = 1;
      el.style.transform = 'translateY(0)';
      // clean inline styles to avoid stacking contexts
      setTimeout(() => { el.style.transform = ''; el.style.transition = ''; }, 300);
    }, delay);
  });

  // button micro-interaction
  document.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('mousedown', () => btn.classList.add('pressed'));
    btn.addEventListener('mouseup', () => btn.classList.remove('pressed'));
    btn.addEventListener('mouseleave', () => btn.classList.remove('pressed'));
  });

  // set progress widths from data-pct to avoid template inline CSS issues
  document.querySelectorAll('.js-progress[data-pct]')
    .forEach(el => {
      const pct = parseFloat(el.getAttribute('data-pct')) || 0;
      el.style.width = Math.max(0, Math.min(100, pct)) + '%';
    });

  // replace feather icons if available
  if (window.feather) {
    try { window.feather.replace(); } catch (e) { /* ignore */ }
  }

  // theme toggle (light / dark) — persisted in localStorage
  const THEME_KEY = 'safeballot_theme';
  function applyTheme(theme) {
    const html = document && document.documentElement;
    if (!html) return;
    if (theme === 'dark') html.classList.add('theme-dark'); else html.classList.remove('theme-dark');
    // update toggle button aria-pressed and icon if present
    const tbtn = document.getElementById('themeToggle');
    const icon = document.getElementById('themeIcon');
    if (tbtn) tbtn.setAttribute('aria-pressed', theme === 'dark');
    if (icon) {
      // swap to sun icon when dark, moon when light (full icons)
      if (theme === 'dark') {
        icon.innerHTML = '<path d="M6.995 12.903a5 5 0 1 1 4.102-8.01 6 6 0 1 0-4.102 8.01z"/>';
        icon.setAttribute('class', 'bi bi-sun-fill');
      } else {
        icon.innerHTML = '<path d="M14.53 10.53a6.5 6.5 0 1 1-8.06-8.06 7 7 0 1 0 8.06 8.06z"/>';
        icon.setAttribute('class', 'bi bi-moon-fill');
      }
    }
  }
  // read persisted
  let theme = localStorage.getItem(THEME_KEY) || 'light';
  applyTheme(theme);
  // attach handler for toggle
  const toggle = document.getElementById('themeToggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      theme = (theme === 'dark') ? 'light' : 'dark';
      localStorage.setItem(THEME_KEY, theme);
      applyTheme(theme);
    });
  // initialize icon state explicitly
  applyTheme(theme);
  }

  // Convert datetime-local inputs to UTC before submitting forms marked with .js-datetime-utc
  document.querySelectorAll('form.js-datetime-utc').forEach(form => {
    form.addEventListener('submit', (ev) => {
      // find inputs of type datetime-local inside this form
      form.querySelectorAll('input[type="datetime-local"]').forEach(input => {
        const val = input.value; // format: 2025-08-29T07:08
        if (!val) return;
        // create a Date object in local time
        const dt = new Date(val);
        if (isNaN(dt.getTime())) return;
        // convert to ISO string in UTC without milliseconds
        const iso = dt.toISOString(); // 2025-08-29T01:08:00.000Z
        // replace input value with ISO without Z (Django DateTimeField will parse with TZ when USE_TZ=True)
        // to be safe, set a data-utc-value attribute and create a hidden input with UTC value
        const hiddenName = input.name + '_utc';
        // remove existing hidden if present
        const existing = form.querySelector('input[name="' + hiddenName + '"]');
        if (existing) existing.remove();
        const h = document.createElement('input');
        h.type = 'hidden';
        h.name = hiddenName;
        h.value = iso; // full ISO with Z
        form.appendChild(h);
      });
    });
  });
});

// Hide page loader once all resources are loaded
window.addEventListener('load', function () {
  try {
    const loader = document.getElementById('page-loader');
    if (!loader) return;
    // If a vote animation exists, allow it to run and keep loader visible for its duration
    const anim = loader.querySelector('.vote-anim');
    if (anim) {
      if (!anim.classList.contains('play')) anim.classList.add('play');
      // keep loader visible for full animation length (3s) then hide
      setTimeout(() => {
        loader.classList.add('hidden');
        setTimeout(() => loader.remove(), 480);
      }, 3000);
      return;
    }
    // fade out
    loader.classList.add('hidden');
    // remove from DOM after transition for accessibility
    setTimeout(() => loader.remove(), 400);
  } catch (e) { /* ignore */ }
});

// Safety fallback: if window.load never fires (hung resource), ensure loader is removed.
(function () {
  const LOADER_ID = 'page-loader';
  const MAX_WAIT = 8000; // ms, maximum time to keep loader
  let removed = false;

  function hideLoader(force) {
    if (removed) return;
    const loader = document.getElementById(LOADER_ID);
    if (!loader) { removed = true; return; }
    // if there's a vote animation and we're not forcing removal, wait for the animation to finish
    const anim = loader.querySelector('.vote-anim');
    if (anim && !force) return;
    // trigger a quick fade
    loader.classList.add('hidden');
    // remove after transition
    setTimeout(() => {
      if (loader && loader.parentNode) loader.remove();
      removed = true;
    }, 450);
  }

  // If DOM is ready but load hasn't fired within a short window, hide loader to avoid infinite spinner
  document.addEventListener('DOMContentLoaded', function () {
    // small delay to let critical render complete
    setTimeout(hideLoader, 250);
  });

  // absolute max timeout (force removal even if animation present)
  setTimeout(() => hideLoader(true), MAX_WAIT);
})();

// Vote casting animation: when loader present, play a short sequence
(function () {
  const loader = document.getElementById('page-loader');
  if (!loader) return;
  const anim = loader.querySelector('.vote-anim');
  if (!anim) return;

  function playVoteAnimation() {
    // add class to play CSS animations
    anim.classList.add('play');
    // stagger confetti shards by adding inline durations/transforms
    const shards = anim.querySelectorAll('.shard');
    shards.forEach((s, i) => {
      const delay = 560 + i * 60; // ms
      s.style.animationDelay = delay + 'ms';
      // give each shard a random rotation and translateX to add variety
      const dx = (Math.random() * 80 - 40) + 'px';
      s.style.transform = 'translateX(' + dx + ')';
    });
    // hide loader after the full animation display time (3s) so it's visible enough
    setTimeout(() => {
      const loaderEl = document.getElementById('page-loader');
      if (!loaderEl) return;
      loaderEl.classList.add('hidden');
      setTimeout(() => loaderEl.remove(), 480);
    }, 3000);
  }

  // Play once after DOM ready (or immediately if already loaded)
  if (document.readyState === 'complete') playVoteAnimation();
  else document.addEventListener('DOMContentLoaded', () => setTimeout(playVoteAnimation, 160));
})();
