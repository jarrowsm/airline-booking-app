const routeBtns = document.querySelectorAll('.routeBtn');

routeBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const ref = btn.getAttribute('data-ref');
    const div = document.getElementById('route-for-' + ref);
    if (!ref || !div) return;

    const isExpanded = btn.getAttribute('aria-expanded') === 'true';
    if (!isExpanded) {
      btn.textContent = 'Hide route';
      div.style.opacity = '1';
      div.style.maxHeight = div.scrollHeight + 'px';
      btn.setAttribute('aria-expanded', 'true');
    } else {
      btn.textContent = 'Show route';
      div.style.opacity = '0';
      div.style.maxHeight = '0';
      btn.setAttribute('aria-expanded', 'false');
    }
  });
});

