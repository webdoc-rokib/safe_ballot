document.addEventListener('DOMContentLoaded', function () {
  // simple fade-in for cards
  document.querySelectorAll('.card').forEach((el, i) => {
    el.style.opacity = 0;
    el.style.transform = 'translateY(8px)';
    setTimeout(() => {
      el.style.transition = 'opacity 300ms ease, transform 300ms ease';
      el.style.opacity = 1;
      el.style.transform = 'translateY(0)';
    }, 60 * i);
  });

  // button micro-interaction
  document.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('mousedown', () => btn.classList.add('pressed'));
    btn.addEventListener('mouseup', () => btn.classList.remove('pressed'));
    btn.addEventListener('mouseleave', () => btn.classList.remove('pressed'));
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
