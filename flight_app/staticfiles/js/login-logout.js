const jsonContent = id => {
  const elem = document.getElementById(id);
  if (!elem) return null;
  return JSON.parse(elem.textContent);
};

let isCustomer = jsonContent('isCustomer');
const indexOnLogout = jsonContent('indexOnLogout');
const refresh = jsonContent('refresh');
const myBookings = jsonContent('myBookings');

const loginBtn = document.getElementById('login-button');
const loginModal = new bootstrap.Modal(document.getElementById('login-modal'));
const loginModalTitle = document.getElementById('login-modal-title');
const loginModalBody = document.getElementById('login-modal-body');
const myBookingsDiv = document.getElementById('my-bookings-div');

loginBtn.addEventListener('click', async () => {
  const resp = await fetch('/login_logout/');
  const { form_html: formHTML } = await resp.json();
  loginModalBody.innerHTML = formHTML;
  loginModal.show();
});

const handleSubmit = async event => {
  const formData = new FormData(event.target);
  const resp = await fetch('/login_logout/', { method: 'POST', body: formData });
  const respJSON = await resp.json();

  if (respJSON.success) {
    loginModal.hide();
    setTimeout(() => {
      if (refresh) location.reload();
      else {
        if (isCustomer) {
          if (indexOnLogout) location.href = '/';
          else {
            isCustomer = false;
            loginBtn.innerHTML = 'Log in';
            loginModalTitle.innerHTML = 'Enter your email from a previous booking';
            myBookingsDiv.innerHTML = '';
          }
        } else {
          isCustomer = true;
          loginBtn.innerHTML = 'Log out';
          loginModalTitle.innerHTML = 'Are you sure you want to log out?';

          if (myBookings) {
            const a = document.createElement('a');
            a.href = '/bookings/';
            a.id = 'my-bookings-button';
            a.className = 'btn btn-outline-light btn-sm border-black text-black';
            a.textContent = 'My bookings';
            myBookingsDiv.appendChild(a);
          }
        }
      }
    }, 300);
  } else loginModalBody.innerHTML = respJSON.form_html;
}

loginModalBody.addEventListener('submit', async event => {
  event.preventDefault();
  await handleSubmit(event);
});

