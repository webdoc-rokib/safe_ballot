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
