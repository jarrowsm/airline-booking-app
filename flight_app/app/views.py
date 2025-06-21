from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
from django.db import IntegrityError
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode
from datetime import datetime, timezone
gmt = timezone.utc

import app.models as m
from app.forms import FlightSearchForm, FlightBookForm, CustomerDetailsForm, EmailForm, ConfirmForm, CancelForm
from app.utils import convert_gmt_offset
from app.views_utils import (
    ParamErrors, validate_airports, parse_search, fix_date_errors, get_result_price_avail,
    get_booking_dict, book_flight, delete_booking, get_schedules, get_price_dict
)


def error_404(request, exception):
    return render(request, '404.html', {}, status=404)


@require_GET
def index(request):
    """
    List airports in the database and render via template.
    """
    customer_id = request.session.get('customer_id')
    customer = m.Customer.objects.get(id=customer_id) if customer_id else None

    depart_id = request.session.get('booking', {}).get('depart_id')
    depart_schedule = (
        m.Schedule.objects
        .select_related('arr_icao')
        .get(id=depart_id)
    ) if depart_id else None

    info = {airport.icao: (airport.name, airport.region) for airport in m.Airport.objects.all()}
    choices = [(icao, f"{region} ({icao})") for icao, (name, region) in info.items()]
    form = FlightSearchForm(origin_choices=choices, destination_choices=choices)

    context = {
        'form': form,
        'customer': customer,
        'is_customer': customer is not None,
        'depart_schedule': depart_schedule,
        'info': info
    }
    return render(request, 'index.html', context)


@require_GET
def destinations(request):
    """
    Return all destinations for an origin as JSON.
    """
    origin = request.GET.get('o', '').upper()

    destinations = (
        m.Schedule.objects
        .filter(dep_icao=origin)
        .values_list('arr_icao', flat=True)
        .distinct()
    )

    if destinations.count() == 0:
        return JsonResponse({'Error': 'Invalid or missing `o` query parameter'}, status=400)

    return JsonResponse({'destinations': list(destinations)})


@require_GET
def flight_dates(request):
    """
    Given origin and destination, return all future dates with non-full flights.
    Used to mark calendar dates.
    """
    origin = request.GET.get('o', '').upper()
    destination = request.GET.get('d', '').upper()

    param_errs, orig_airport, dest_airport = validate_airports(origin, destination)

    if param_errs:
        return JsonResponse({'Error': param_errs}, status=400)

    orig_tz = convert_gmt_offset(orig_airport.gmt_offset)
    dates = [
        s[0].astimezone(orig_tz).date()
        for s in m.Schedule.objects
            .filter(
                dep_icao=origin,
                arr_icao=destination,
                seats_avail__gte=1,
                dep_dt__gte=datetime.now(gmt)
            )
            .values_list('dep_dt')
            .distinct()
    ]
    return JsonResponse({'dates': dates})


@require_http_methods(['GET', 'POST'])
def flights(request):
    """
    GET:  Construct a form for selecting one-way or return flights in
          local 24h windows, and show the prices for other flights in
          that week.
    POST: Validate the flight selections and redirect to register or
          resend the form with errors.
    """
    if request.method == 'GET':
        request.session['search_path'] = request.get_full_path()

        try:
            orig_airport, dest_airport, dates, travellers = parse_search(request)
        except ParamErrors as e:
            return render(request, 'error.html', {'h2': 'Search error!', 'errors': e.param_errs})

        search = {
            'origin': orig_airport,
            'destination': dest_airport,
            'depart_date': dates['depart'].date(),
            'return_date': dates['return'].date() if dates.get('return') else None,
            'travellers': travellers,
        }

        # Redirect if dates are invalid
        date_err, search = fix_date_errors(dates, search)

        if date_err:
            search.update({'origin': orig_airport.icao, 'destination': dest_airport.icao})
            if search.get('return_date') is None:
                search.pop('return_date', None)
            return redirect(reverse('flights') + '?' + urlencode(search))

        results = {'depart': [], 'return': []}
        week_price_avail = {'depart': [], 'return': []}

        results['depart'], week_price_avail['depart'] = get_result_price_avail(
            date=dates['depart'],
            depart_gmt_offset=orig_airport.gmt_offset,
            origin=orig_airport.icao,
            destination=dest_airport.icao, 
            remove_before_now=True
        )

        if dates.get('return'):
            results['return'], week_price_avail['return'] = get_result_price_avail(
                date=dates['return'],
                depart_gmt_offset=dest_airport.gmt_offset,
                origin=dest_airport.icao,
                destination=orig_airport.icao,
                remove_before_now=True
            )

        request.session['travellers'] = travellers
        prices = request.session['prices'] = {s.id: s.current_price for s in results['depart'] + results['return']}

        depart_choices = request.session['depart_choices'] = [(str(s.id), '') for s in results['depart']]
        return_choices = request.session['return_choices'] = [(str(s.id), '') for s in results['return']]
        form = FlightBookForm(depart_choices=depart_choices, return_choices=return_choices)

        context = {
            'is_customer': request.session.get('customer_id') is not None,
            'search': search,
            'results': results,
            'week_price_avail': week_price_avail,
            'form': form,
            'messages': messages.get_messages(request),
        }
        return render(request, 'flights.html', context)

    else:  # POST - process form submission
        form = FlightBookForm(
            request.POST,
            depart_choices=request.session.get('depart_choices'),
            return_choices=request.session.get('return_choices')
        )

        if form.is_valid():
            depart_schedule, return_schedule = get_schedules(
                form.cleaned_data['select_depart'],
                form.cleaned_data.get('select_return'),
                include_None=True
            )
            depart_seats = depart_schedule.seats_avail
            return_seats = return_schedule.seats_avail if return_schedule else None

            if depart_seats == 0:
                form.add_error('select_depart', 'Selected outbound flight is full.')
            if return_seats == 0:
                form.add_error('select_return', 'Selected return flight is full.')

            if return_schedule and depart_schedule.arr_dt >= return_schedule.dep_dt:
                form.add_error('select_return', 'Return flight must depart after outbound flight arrives.')

            if not form.errors:
                request.session['booking'] = get_booking_dict(
                    request.session.get('prices'),
                    request.session.get('travellers'),
                    depart_schedule.id,
                    depart_seats,
                    return_schedule.id if return_schedule else None,
                    return_seats
                )
                return redirect('register')

        # GET + messages to keep query params
        for errs in form.errors.values():
            for err in errs:
                messages.error(request, err)
        return redirect(request.session.get('search_path'))


@require_http_methods(['GET', 'POST'])
def register(request):
    """
    GET:  Provide the registration form.
    POST: Validate form (unique email) and proceed to index or
          confirmation, depending on whether a booking is in process.
    """
    booking = request.session.get('booking')
    if not booking:
        return redirect('index')

    if request.GET.get('action') == 'modify':
        # User clicked 'go back'
        if sp := request.session.get('search_path'):
            return redirect(sp)

    schedules = get_schedules(booking['depart_id'], booking['return_id'])
    email_form = EmailForm(request.POST or None)
    customer_form = CustomerDetailsForm(request.POST or None)

    context = {
        'booking': booking,
        'schedules': schedules,
        'email_form': email_form,
        'customer_form': customer_form
    }

    if cid := request.session.get('customer_id', None):
        context['customer'] = m.Customer.objects.get(id=cid)

    def confirm_as(new_id):
        request.session['customer_id'] = new_id
        return redirect('confirm')

    if request.method == 'POST':
        if customer_form.is_valid():
            try:
                customer = m.Customer(**customer_form.cleaned_data)
                customer.save()
                return confirm_as(customer.id)
            except IntegrityError:
                customer_form.add_error('email', 'This email is already registered.')
                context['customer_form'] = customer_form
                return render(request, 'register.html', context)

        elif email_form.is_valid():
            email = email_form.cleaned_data['email']
            try:
                customer = m.Customer.objects.get(email=email)
                return confirm_as(customer.id)
            except m.Customer.DoesNotExist:
                email_form.add_error('email', 'Email is not registered.')
    
    return render(request, 'register.html', context)


@require_http_methods(['GET', 'POST'])
def login_logout(request):
    """
    Check whether customer ID is in the session and render the email (login) or
    confirm (logout) form accordingly. The form is formatted in
    templates/partials/login_logout_form.html and the rendered HTML is then
    JSON-serialised to form the repsonse to the AJAX request in static/login-logout.js,
    where it is inserted into the modal in templates/partials/login_logout_modal.html.

    GET:  Send email form or confirm form
    POST: Validate form and send another JSON response
    """
    cid = request.session.get('customer_id')
    old_customer = m.Customer.objects.get(id=cid) if cid else None
    form = (
        ConfirmForm(request.POST or None) if old_customer else
        EmailForm(request.POST or None, placeholder='\n')
    )

    def form_json():
        context = {'customer': old_customer, 'form': form}
        html = render_to_string("partials/login_logout_form.html", context, request)
        return JsonResponse({'success': False, 'form_html': html})

    if request.method == 'POST':
        if form.is_valid():
            if not old_customer:
                # Log in
                email = form.cleaned_data['email']

                try:
                    customer = m.Customer.objects.get(email=email)
                    request.session['customer_id'] = customer.id
                    return JsonResponse({'success': True})
                except m.Customer.DoesNotExist:
                    form.add_error('email', 'Invalid email')

                return form_json()
            else:
                # Log out
                del request.session['customer_id']
                return JsonResponse({'success': True})

    return form_json()


@require_http_methods(['GET', 'POST'])
def confirm(request):
    """
    GET:  Show the confirmation form.
    POST: Book the flight: append to Bookings, decrement seats_avail in Schedule
          and show invoice.
    """
    customer_id = request.session.get('customer_id')
    booking = request.session.get('booking')

    if request.method == 'POST' and not booking:
        return render(
            request,
            'error.html',
            {
                'h2': 'Error',
                'errors': ['Booking not available'],
                'link': 'bookings',
                'link_text': 'All bookings'
            })
    if not booking:
        return redirect('index')
    if not customer_id:
        return redirect('register')

    customer = m.Customer.objects.get(id=customer_id)
    form = ConfirmForm(request.POST or None)

    if request.method == 'GET' or not form.is_valid():
        context = {
            'schedules': get_schedules(booking['depart_id'], booking['return_id']),
            'booking': booking,
            'customer': customer,
            'form': form
        }
        return render(request, 'confirm.html', context)
    
    ref = book_flight(
        tickets=booking['tickets'],
        customer=customer,
        depart_schedule=booking['depart_id'],
        depart_price=booking['prices']['depart'],
        return_schedule=booking['return_id'],
        return_price=booking['prices']['return']
    )
    del request.session['booking']
    request.session['book_ref'] = ref
    return redirect('bookings')


@require_http_methods(['GET', 'POST'])
def bookings(request):
    """
    GET:  Show bookings if customer exists in session - book_ref and cancel_ref tell the
          template whether to display a thank you or confirmation message.
    POST: Validate then cancel a booking
    """
    err = render(
        request,
        'error.html',
        {
            'h2': 'Error',
            'errors': ['Error in trying to cancel booking.'],
            'link': 'bookings',
            'link_text': 'All bookings'
        })

    if cid := request.session.get('customer_id'):
        customer = m.Customer.objects.get(id=cid)
    else:
        if request.method == 'POST':
            return err
        return render(request, 'bookings.html', {})

    form = CancelForm(request.POST or None)

    if form.is_valid():
        if ref := form.cleaned_data.get('ref'):
            try:
                booking = m.Booking.objects.select_related('customer', 'depart_schedule', 'return_schedule').get(ref=ref)
                if booking.customer != customer:
                    return err
            except m.Booking.DoesNotExist:
                return err
        else:
            return err

        delete_booking(booking)
        request.session['cancel_ref'] = ref
        return redirect('bookings')

    bookings = (
        m.Booking.objects
        .select_related('depart_schedule', 'return_schedule')
        .filter(customer=customer)
    )
    context = {
        'bookings': bookings,
        'customer': customer,
        'is_customer': True,
        'book_ref': request.session.pop('book_ref', None),
        'cancel_ref': request.session.pop('cancel_ref', None),
        'form': form
    }
    return render(request, 'bookings.html', context)


@require_GET
def invoice(request):
    """
    Render the invoice provided a reference in the query parameters.
    """
    cid = request.session.get('customer_id')
    booking_ref = request.GET.get('ref')

    err = {'h2': 'Error', 'link': 'bookings', 'link_text': 'All bookings'}

    if not cid:
        return redirect('register')
    if not booking_ref:
        err.update({'errors': ['Missing `ref` query parameter.']})
        return render(request,'error.html', err)

    customer = m.Customer.objects.get(id=cid)
    try:
        booking = m.Booking.objects.select_related('depart_schedule', 'return_schedule').get(ref=booking_ref)
        prices = get_price_dict(booking.tickets, booking.depart_price, booking.return_price)
        schedules = [booking.depart_schedule]
        if booking.return_schedule:
            schedules.append(booking.return_schedule)

        context = {'booking': booking, 'schedules': schedules, 'prices': prices, 'customer': customer }
        return render(request, 'invoice.html', context)
    except m.Booking.DoesNotExist:
        err.update({'errors': ['Invalid booking reference.']})
        return render(request, 'error.html', err)

