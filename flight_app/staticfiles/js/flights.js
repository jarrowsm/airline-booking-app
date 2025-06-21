const nTrav = parseInt(new URLSearchParams(window.location.search).get('travellers'), 10);
const form = document.getElementById('flights-form');
const radioBtns = form.querySelectorAll('input[type="radio"]');

// Toast if too few seats
radioBtns.forEach(btn => {
  btn.addEventListener('change', () => {
    if (!btn.checked) return;

    const seats = parseInt(btn.dataset.seats, 10);
    if (seats === 0) return;  // handled server-side

    document.querySelectorAll('.toast').forEach(toast => { toast.remove(); });

    if (seats < nTrav) {
      const toast = document.createElement('div');
      toast.innerHTML = `
        <div class="toast-header">
          <b class="me-4">Not enough seats!</b>
          <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">
          Your booking will include the ${seats} available seat${seats === 1 ? '' : 's'}.
        </div>`;
      toast.classList.add('toast');
      btn.closest('.card').getElementsByClassName('toast-container')[0].appendChild(toast);
      new bootstrap.Toast(toast).show();
    }
  });
});

