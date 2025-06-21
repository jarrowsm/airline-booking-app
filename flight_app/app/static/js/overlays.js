document.querySelectorAll('.msg-toast')
  .forEach(elem => new bootstrap.Toast(elem).show());
document.querySelectorAll('.flight-info-popover')
  .forEach(elem => new bootstrap.Popover(elem, { trigger: 'hover' }));

