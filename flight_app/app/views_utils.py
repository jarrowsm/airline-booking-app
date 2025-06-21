"""
Utility functions for views.py.
"""

from typing import Optional
from datetime import datetime, date, timedelta, timezone
gmt = timezone.utc

import app.models as m
from app.utils import gmt_range_about, generate_booking_ref


class ParamErrors(Exception):
    def __init__(self, param_errs):
        self.param_errs = param_errs


def validate_airports(origin: str, destination: str) -> list:
    param_errs, orig_airport, dest_airport = [], None, None

    if origin and destination:
        try:
            orig_airport = m.Airport.objects.get(icao=origin)
            dest_airport = m.Airport.objects.get(icao=destination)
            if orig_airport == dest_airport:
                param_errs.append('Origin and destination cannot be the same.')
        except m.Airport.DoesNotExist:
            param_errs.append('Invalid origin and/or destination.')
    else:
        param_errs.append('Origin and destination are required.')

    return param_errs, orig_airport, dest_airport


def parse_search(request):
    origin = request.GET.get('origin', '').upper()
    destination = request.GET.get('destination', '').upper()
    depart_date_str = request.GET.get('depart_date')
    return_date_str = request.GET.get('return_date')
    travellers_str = request.GET.get('travellers')

    param_errs, dates = [], {}

    if not depart_date_str:
        param_errs.append('Departure date is required.')
    else:
        try:
            dates['depart'] = datetime.strptime(depart_date_str, '%Y-%m-%d')
        except ValueError:
            param_errs.append('Invalid departure date.')

    if return_date_str:
        try:
            dates['return'] = datetime.strptime(return_date_str, '%Y-%m-%d')
        except ValueError:
            param_errs.append('Invalid return date.')

    airport_errs, orig_airport, dest_airport = validate_airports(origin, destination)
    param_errs.extend(airport_errs)

    if not travellers_str:
        param_errs.append('Number of travellers is required.')
    else:
        try:
            travellers = int(travellers_str)
            if travellers < 1 or travellers > 6:
                raise ValueError()
        except ValueError:
            param_errs.append('Invalid number of travellers.')

    if param_errs:
        raise ParamErrors(param_errs)

    return orig_airport, dest_airport, dates, travellers


def fix_date_errors(dates: dict, search: dict) -> tuple[bool, dict]:
    today = datetime.now(gmt).date()
    date_err = False

    if dates['depart'].date() < today:
        search['depart_date'] = today.strftime('%Y-%m-%d')
        date_err = True

    if dates.get('return') and dates['return'] < dates['depart']:
        search['return_date'] = search['depart_date']
        date_err = True

    return date_err, search


def flights_on_date(
    date: date,
    depart_gmt_offset: str,
    origin: str,
    destination: str,
    remove_before_now=False
) -> list[m.Schedule]:
    """
    Query flights within 24 hours w.r.t. the departure timezone
    """
    start, end = gmt_range_about(date, depart_gmt_offset)
    if remove_before_now:
        now = datetime.now(gmt)
        if start < now:
            start = now

    schedules = list(
        m.Schedule.objects.filter(
            dep_icao=origin,
            arr_icao=destination,
            dep_dt__gte=start,
            dep_dt__lt=end,
        )
    )
    return schedules


def flights_in_week(
    date: date,
    depart_gmt_offset: str,
    origin: str,
    destination: str,
    remove_before_now=False
) -> list[tuple[date, list[m.Schedule]]]:
    """
    Query flights in week about `date`
    """
    result = []
    for d in range(-3, 4):
        curr = date + timedelta(days=d)
        if remove_before_now and curr.date() < datetime.now(gmt).date():
            s = []
        else:
            s = flights_on_date(
                curr,
                depart_gmt_offset,
                origin,
                destination,
                remove_before_now=remove_before_now
            )
        result.append((curr.date(), s))
    
    return result



def price_availability(schedules: list[m.Schedule]) -> tuple[Optional[float], bool]:
    # No flights
    if not schedules:
        return None, False

    # Flight(s) with seats -> show minimum price with seats
    if avail_prices := [s.current_price for s in schedules if s.seats_avail >= 1]:
        return min(avail_prices), True

    # Flight(s) but no seats -> show old min price
    return min(s.current_price for s in schedules), False


def get_result_price_avail(
    date: date,
    depart_gmt_offset: str,
    origin: str,
    destination: str,
    remove_before_now=False
) -> tuple[list[m.Schedule], list[tuple[date, Optional[float], bool]]]:
    """
    Given a date, return the flights for that date and the prices + seat availabilty
    for the week.
    """
    depart_week = flights_in_week(date, depart_gmt_offset, origin, destination, remove_before_now)
    result = depart_week[3][1]
    week_price_avail = [(d, *price_availability(s)) for d, s in depart_week]
    return result, week_price_avail


def get_schedules(
    depart_id: int | str,
    return_id: Optional[int | str] = None,
    include_None=False
) -> list[m.Schedule, Optional[m.Schedule]]:
    return_id = return_id or None
    depart_id = int(depart_id) if isinstance(depart_id, str) else depart_id
    return_id = int(return_id) if isinstance(return_id, str) else return_id if return_id is not None else None

    depart_schedule = m.Schedule.objects.get(id=depart_id)
    return_schedule = m.Schedule.objects.get(id=return_id) if return_id else None

    if not include_None and not return_schedule:
        return [depart_schedule]

    return [depart_schedule, return_schedule]


def get_price_dict(tickets: int, depart_price: float, return_price: Optional[float]=None) -> dict[float]:
    return {
        'depart': depart_price,
        'return': return_price,
        'total': (depart_price + (return_price or 0)) * tickets
    }


def get_booking_dict(
    prices: dict,
    travellers: int,
    depart_schedule_id: int,
    depart_seats: int,
    return_schedule_id: Optional[int]=None,
    return_seats: Optional[int]=None
) -> dict:
    """
    Create a booking with the advertised price and correct number of seats
    """
    depart_price = prices[str(depart_schedule_id)]
    return_price = prices[str(return_schedule_id)] if return_schedule_id else None
    tickets = min(travellers, depart_seats, return_seats or float('inf'))
    booking = {
        'depart_id': depart_schedule_id,
        'return_id': return_schedule_id,
        'tickets': tickets,
        'prices': get_price_dict(tickets, depart_price, return_price)
    }
    return booking


def unique_booking_ref(length=6):
    while True:
        booking_ref = generate_booking_ref(length)
        if not m.Booking.objects.filter(ref=booking_ref).exists():
            return booking_ref


def book_flight(
    tickets: int,
    customer: int | m.Customer,
    depart_schedule: int | m.Schedule,
    depart_price: float,
    return_schedule: Optional[int | m.Schedule]=None,
    return_price: Optional[float]=None
) -> int:
    if isinstance(customer, int):
        customer = m.Customer.objects.get(id=customer)
    if isinstance(depart_schedule, int):
        depart_schedule = m.Schedule.objects.get(id=depart_schedule)
    if isinstance(return_schedule, int):
        return_schedule = m.Schedule.objects.get(id=return_schedule)

    booking = m.Booking(
        ref=unique_booking_ref(),
        tickets=tickets,
        customer=customer,
        depart_schedule=depart_schedule,
        return_schedule=return_schedule,
        depart_price=depart_price,
        return_price=return_price
    )
    booking.save()

    for schedule in [depart_schedule, return_schedule]:
        if schedule:
            schedule.seats_avail -= tickets
            schedule.save()

    return booking.ref


def delete_booking(booking: m.Booking) -> None:
    for schedule in [booking.depart_schedule, booking.return_schedule]:
        if schedule:
            schedule.seats_avail += booking.tickets
            schedule.save()
    booking.delete()

