const TODAY = new Date().toISOString().split('T')[0];

const airports = JSON.parse(document.getElementById('airports').textContent);

const get = id => { return document.getElementById(id) };
const isReturnCheckbox = get('is_return');
const origSelect = get('id_origin');
const destSelect = get('id_destination');
const departField = get('id_depart_date');
const returnDiv = get('return');
const returnField = get('id_return_date');
const searchButton = get('search-button');
const nTrav = get('id_travellers');
const decTrav = get('dec-travellers');
const incTrav = get('inc-travellers');
const travDisplay = get('travellers-display');
const swapBtn = get('swap-btn');

let departCal, returnCal, noFlights, origChoices, destChoices;

/*** Airport selection ***/
// initialise choices.js selectors
choicesClassNames = {
  containerOuter: ['choices', 'lg-width-240'],
  containerInner: ['choices__inner', 'bg-white', 'text-center'],
}

origChoices = new Choices(origSelect, {
  searchEnabled: true,
  itemSelectText: '',
  shouldSort: false,
  placeholder: false,
  classNames: choicesClassNames,
});

destChoices = new Choices(destSelect, {
  searchEnabled: true,
  itemSelectText: '',
  shouldSort: false,
  placeholder: false,
  classNames: choicesClassNames
});


/*** Date selection ***/
// fallback
departField.min = TODAY;
returnField.min = TODAY;

// initialise flatpickr calendars
departCal = flatpickr(departField, {
  minDate: TODAY,
  dateFormat: "Y-m-d",
  altInput: true,
  altFormat: "j/n/y",
});

returnCal = flatpickr(returnField, {
  minDate: TODAY,
  dateFormat: "Y-m-d",
  altInput: true,
  altFormat: "j/n/y"
});

// mark calendar dates with flights
setUpDateMarking(departCal);
setUpDateMarking(returnCal);

// dynamically set destination airports
setDestinations().then(() => markFlightDates());

// also do when origin/destination changes
origSelect.addEventListener('change', async () => {
  await setDestinations();
  markFlightDates();
});

destSelect.addEventListener('change', markFlightDates);

/*** Swap origin/destination button ***/
swapBtn.addEventListener('click', swapOrigDest);

/*** 'Return trip?' checkbox ***/
disableReturnField();

isReturnCheckbox.addEventListener('change', () => {
  if (isReturnCheckbox.checked && !noFlights) {
    returnField.disabled = false;
    if (returnCal) returnCal._input.disabled = false;
    updateReturnField();
  } else {
    disableReturnField();
  }
});

departField.addEventListener('change', updateReturnField);

/*** Increase/decrease travellers buttons ***/
const updateTravDisplay = () => travDisplay.textContent = nTrav.value;

updateTravDisplay()

decTrav.addEventListener('click', () => {
  const n = parseInt(nTrav.value);
  if (n > 1) {
    nTrav.value = n - 1;
    updateTravDisplay();
  }
});

incTrav.addEventListener('click', () => {
  const n = parseInt(nTrav.value);
  if (n < 6) {
    nTrav.value = n + 1;
    updateTravDisplay();
  }
});

/*** Featured destinations banners ***/
const banners = [
  document.getElementById('rotorua-banner'),
  document.getElementById('melbourne-banner')
];

banners[0].addEventListener('click', () => { bannerClick('NZRO', banners); });
banners[1].addEventListener('click', () => { bannerClick('YMML', banners); });


////////////////////////////////////////////////

function nextDate(dateSet, dateStr) {
  // Return next date from dateSet on or after dateStr
  const date = new Date(dateStr);
  const dateArr = [];
  for (const d of dateSet) {
    if (new Date(d) >= date) dateArr.push(d);
  }
  if (dateArr.length === 0) return null;
  return dateArr[0];
}

function updateReturnField() {
  if (returnField.disabled) return;
  // Update min dates
  returnField.min = departField.value || TODAY;  // native
  returnCal.set('minDate', departField.value || TODAY);

  // Update selected dates
  let nextReturn;
  const nextDepart = nextDate(departCal.markedDates, departField.value);
  if (nextDepart) nextReturn = nextDate(returnCal.markedDates, nextDepart);
  if (nextReturn) returnCal.setDate(nextReturn, true);
}

function disableReturnField() {
  returnField.disabled = true;
  returnField.value = '';
  if (returnCal) {
    returnCal._input.disabled = true;
    returnCal.setDate()
  }
}

async function setDestinations() {
  // fetch destinations based on origin and fill selector
  const resp = await fetch(`/destinations?o=${origSelect.value}`);
  const { destinations: icaos } = await resp.json();

  if (!icaos) {
    noFlights = true
    return;
  }

  const currentIcao = destSelect.value;

  destSelect.innerHTML = '';
  if (destChoices) destChoices.clearStore();

  if (icaos.length === 0) {
    noFlights = true;
    searchButton.disabled = true;

    destSelect.disabled = true;
    destSelect.innerHTML = '<option>No flights available</option>'

    if (destChoices) {
      const choiceArr = [{ value: '', label: 'No flights available', disabled: true }];
      destChoices.setChoices(choiceArr, 'value', 'label', false);
    }

    departField.disabled = true;
    returnField.disabled = true;

    const disableFp = fpCal => {
      if (!fpCal) return;
      fpCal._input.disabled = true;
      fpCal.setDate();
    }

    if (departCal) disableFp(departCal);
    if (returnCal) disableFp(returnCal);
  } else {
    noFlights = false;
    searchButton.disabled = false;
    destSelect.disabled = false;
    departField.disabled = false;
    if (departCal) departCal._input.disabled = false;

    // set as selected or first
    const selected = icaos.includes(currentIcao) ? currentIcao : icaos[0];
    const label = icao => `${airports[icao][1]} (${icao})`;

    destSelect.value = selected;

    if (destChoices) {
      const choiceArr = [];
      for (const icao of icaos) {
        choiceArr.push({ value: icao, label: label(icao), selected: (icao === selected) });
      }
      destChoices.setChoices(choiceArr, 'value', 'label', true);
    } else {
      // fallback
      for (const icao of icaos) {
        const option = document.createElement('option');
        option.value = icao;
        option.textContent = label(icao),
        destSelect.appendChild(option);
      }
    }
  }
}

async function swapOrigDest() {
  const origVal = origSelect.value;
  const destVal = destSelect.value;

  origSelect.value = destVal;
  if (origChoices) origChoices.setChoiceByValue(destVal);

  await setDestinations();

  destSelect.value = origVal;
  if (destChoices) destChoices.setChoiceByValue(origVal);

  markFlightDates();
}

function getDateMarkerer(fpCal) {
  return (dateObj, dateStr, flatpickr, dayElem) => {
    // Called by Flatpickr onDayCreate callback,
    // compares current date to marked set and adds mark
    const dateStr1 = flatpickr.formatDate(dayElem.dateObj, "Y-m-d");
    if (fpCal.markedDates.has(dateStr1)) {
      const createMark = () => {
        const mark = document.createElement('span');
        mark.classList.add('date-mark');
        return mark;
      }
      dayElem.appendChild(createMark());
    }
  };
}

function setUpDateMarking(fpCal) {
  fpCal.markedDates = new Set();
  fpCal.config.onDayCreate.push(getDateMarkerer(fpCal));
}

async function markFlightDates() {
  // Fetch depart and return flight dates, filter out dates before today,
  // and append to respective calendar's marked set and redraw

  if (noFlights || !departCal || !returnCal) return;

  const resp1 = await fetch(`/flight_dates/?o=${origSelect.value}&d=${destSelect.value}`);
  const { dates: departDates } = await resp1.json();

  const resp2 = await fetch(`/flight_dates/?o=${destSelect.value}&d=${origSelect.value}`);
  const { dates: returnDates} = await resp2.json();

  departCal.markedDates.clear();
  returnCal.markedDates.clear();

  const futureDates = dates => dates >= TODAY;
  const removePrev = dates => dates.filter(futureDates);

  removePrev(departDates).forEach(date => departCal.markedDates.add(date));
  removePrev(returnDates).forEach(date => returnCal.markedDates.add(date));

  departCal.setDate([...departCal.markedDates][0]);
  if (isReturnCheckbox.checked) updateReturnField();

  departCal.redraw();
  returnCal.redraw();
}

const fadeShadow = async elem => {
  elem.classList.add('white-shadow');

  await new Promise(resolve => setTimeout(resolve, 1500));

  elem.classList.add('shadow-fade-out');
  elem.classList.remove('white-shadow');

  await new Promise(resolve => {
    // resolve on transitionend
    const onEnd = () => {
      elem.removeEventListener('transitionend', onEnd);
      resolve();
    };
    elem.addEventListener('transitionend', onEnd);
  });

  elem.classList.remove('shadow-fade-out');
};

async function bannerClick(dest, banners) {
  banners.forEach(banner => banner.classList.add('disabled'));

  origSelect.value = 'NZNE';
  if (origChoices) origChoices.setChoiceByValue('NZNE');

  await setDestinations();

  destSelect.value = dest;
  if (destChoices) destChoices.setChoiceByValue(dest);

  markFlightDates();

  window.scrollTo({ top: 0, behavior: 'smooth' });

  const elem = destChoices ? document.querySelector('#dest .choices') : destSelect;
  await fadeShadow(elem);

  banners.forEach(banner => banner.classList.remove('disabled'));
}

