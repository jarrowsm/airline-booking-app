"""
Standalone script to populate the database.
Instructions:
    Run with --no-synth to populate tables known at design-time (Aircraft, Airport, Schedule),
    alternatively, --no-basic will only populate Customer and Booking with synthetic data.
    Running without either argument will populate all of the above.
    You may also choose to modify 3 variables:
        SCHEDULE_DAYS controls the number of days from today to insert into Schedule
        SYNTH_CUSTOMERS controls the number of synthetic customers to generate
        SYNTH_BOOKINGS controls the number of synthetic bookings
Synthetic data
    Customer rows contain a title, first-name, last-name, sex and email derived from randomnames.csv.
    Booking rows consist of a random customer asigned to a random departure Schedule and possibly also return
    Schedule. The reference and prices are dynamically allocated (prices are based on the number of seats
    remaining and days until departure).
"""

import os
import csv
import random
import argparse
import urllib.parse
from tqdm import tqdm

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flight_app.settings')

import django
django.setup()

import app.models as m
import app.utils as utils
from app.views_utils import book_flight


SCHEDULE_DAYS = 100  # from today

SYNTH_CUSTOMERS = 400

SYNTH_BOOKINGS = 500

# Name, Brand, Max seats
AIRCRAFT = [
    ('SJ30i', 'SyberJet', 6),
    ('SF50',  'Cirrus',   4),
    ('Elite', 'HondaJet', 5),
]

# ICAO, Name, Region, GMT offset
AIRPORTS = [
    ('NZNE', 'North Shore Dairy Flat Airport', 'Auckland North Shore',    '+12:00'),
    ('NZRO', 'Rotorua Airport',                'Rotorua / Bay of Plenty', '+12:00'),
    ('NZCI', 'Tuuta Airport',                  'Chatham Islands',         '+12:45'),
    ('NZGB', 'Claris Airport',                 'Great Barrier Island',    '+12:00'),
    ('NZTL', 'Lake Tekapo Airport',            'Mackenzie District',      '+12:00'),
    ('YMML', 'Melbourne Airport',              'Victoria, Australia',     '+10:00'),
]

# Origin, Destination, Local departure time, Local arrival time, Aircraft, Operating days, Base price
WEEKLY_FLIGHT_SCHEDULE = [
    ('NZNE', 'YMML', '10:05', '4:10', 'SJ30i', ('fri',),                        250),
    ('YMML', 'NZNE', '15:30', '3:35', 'SJ30i', ('sun',),                        230),
    ('NZNE', 'NZRO', '06:00', '0:45', 'SF50',  ('mon','tue','wed','thu','fri'),  74),
    ('NZRO', 'NZNE', '10:30', '0:45', 'SF50',  ('mon','tue','wed','thu','fri'),  80),
    ('NZNE', 'NZRO', '17:35', '0:45', 'SF50',  ('mon','tue','wed','thu','fri'),  80),
    ('NZRO', 'NZNE', '23:30', '0:45', 'SF50',  ('mon','tue','wed','thu','fri'),  80),
    ('NZNE', 'NZGB', '08:00', '0:30', 'SF50',  ('mon','wed','fri'),             130),
    ('NZGB', 'NZNE', '09:00', '0:30', 'SF50',  ('tue','thu','sat'),             130),
    ('NZNE', 'NZCI', '09:30', '2:30', 'Elite', ('tue', 'fri'),                  190),
    ('NZCI', 'NZNE', '22:50', '2:30', 'Elite', ('wed', 'sat'),                  190),
    ('NZNE', 'NZTL', '10:00', '1:30', 'Elite', ('mon',),                        150),
    ('NZTL', 'NZNE', '16:35', '1:30', 'Elite', ('tue',),                        150),
]


def set_aircraft():
    for info in tqdm(AIRCRAFT):
        a = m.Aircraft(*info)
        a.save()


def set_airport():
    for info in tqdm(AIRPORTS):
        a = m.Airport(*info)
        a.save()


def set_schedule():
    sched_list = [
        dict(zip(['dep_icao', 'arr_icao', 'dep_time', 'duration', 'aircraft', 'days', 'price'], i))
        for i in WEEKLY_FLIGHT_SCHEDULE
    ]
    max_seats = {i[0]: i[2] for i in AIRCRAFT}
    gmt_offsets = {i[0]: i[-1] for i in AIRPORTS}

    for i, s in enumerate(sched_list):
        s['flight_no'] = utils.format_flight_no(i+1)

    for date in tqdm(utils.project_dates(SCHEDULE_DAYS)):
        flights = utils.flights_on_date(date, sched_list)

        for f in flights:
            dep_dt, arr_dt = utils.duration_to_datetimes(
                dep_date=date,
                dep_time=f['dep_time'],
                duration=f['duration'],
                dep_gmt_offset=gmt_offsets[f['dep_icao']]
            )
            s = m.Schedule(
                flight_no=f['flight_no'],
                dep_dt=dep_dt,
                arr_dt=arr_dt,
                seats_avail=max_seats[f['aircraft']],
                aircraft_id=f['aircraft'],
                dep_icao_id=f['dep_icao'],
                arr_icao_id=f['arr_icao'],
                base_price=f['price'],
            )
            s.save()


def set_customer():
    """
    Populate Customer with synthetic data.
    """
    customers = utils.rand_csv_rows('randomnames.csv', SYNTH_CUSTOMERS)
    customers = [i[1:] for i in customers]  # Remove ID
    customers = [dict(zip(['title', 'fname', 'lname', 'sex', 'email'], i)) for i in customers]
    customers = utils.del_dupl_vals(customers, 'email')  # UNIQUE constraint

    for customer in tqdm(customers):
        c = m.Customer(**customer)
        c.save()


def set_booking():
    """
    Populate Booking with random data using Customer and Schedule.
    """
    bookings = []
    skip_count = 0

    for _ in tqdm(range(SYNTH_BOOKINGS), desc='Generating bookings'):
        try:
            customer = utils.random_instance(m.Customer)

            depart_schedule = utils.random_instance(m.Schedule, seats_avail__gte=1)
            depart_price = depart_schedule.current_price

            # Biased to more seats but simulates n_travellers in search menu
            tickets = min(random.randint(1, 6), depart_schedule.aircraft.max_seats)

            # Assign random return trips to half
            if random.randint(0, 1):
                return_schedule = utils.random_instance(
                    m.Schedule,
                    dep_icao=depart_schedule.arr_icao,
                    arr_icao=depart_schedule.dep_icao,
                    dep_dt__gt=depart_schedule.arr_dt,
                    seats_avail__gte=tickets
                )
                return_price = return_schedule.current_price
            else:
                return_schedule = return_price = None
            
            bookings.append({
                'tickets': tickets,
                'customer': customer,
                'depart_schedule': depart_schedule,
                'return_schedule': return_schedule,
                'depart_price': depart_price,
                'return_price': return_price,
            })
        except ValueError as e:
            skip_count += 1
            continue

    if skip_count > 0:
        print(f'Skipping {skip_count} inconsistent bookings')

    for booking in tqdm(bookings, desc='Saving bookings'):
        book_flight(**booking)


def main():
    tables = {
        'basic': (
            (set_aircraft, 'Aircraft'),
            (set_airport, 'Airport'),
            (set_schedule, 'Schedule'),
        ),
        'synth': (
            (set_customer, 'Customer'),
            (set_booking, 'Booking'),
        ),
    }

    parser = argparse.ArgumentParser(description='Populate the database')
    parser.add_argument(
        '--no-basic',
        action='store_true', default=False,
        help=f"Exclude basic data ({', '.join([i[1] for i in tables['basic']])})"
    )
    parser.add_argument(
        '--no-synth',
        action='store_true', default=False,
        help=f"Exclude synthetic data ({', '.join([i[1] for i in tables['synth']])})"
    )

    global SCHEDULE_DAYS, SYNTH_CUSTOMERS, SYNTH_BOOKINGS

    parser.add_argument(
        '--schedule-days',
        type=int,
        default=SCHEDULE_DAYS,
        help='Number of days ahead of today to insert into Schedule'
    )
    parser.add_argument(
        '--customers',
        type=int,
        default=SYNTH_CUSTOMERS,
        help='Number of synthetic rows to insert into Customer'
    )
    parser.add_argument(
        '--bookings',
        type=int,
        default=SYNTH_BOOKINGS,
        help='Number of synthetic rows to insert into Bookings'
    )

    args = parser.parse_args()
    
    SCHEDULE_DAYS = args.schedule_days
    SYNTH_CUSTOMERS = args.customers
    SYNTH_BOOKINGS = args.bookings

    for k, v in tables.items():
        if not getattr(args, f'no_{k}'):
            for f, tbl in v:
                print(f'Inserting {k} data into {tbl}')
                f()


if __name__ == '__main__':
    print('\nPriming database')
    main()
    print('Done\n')

