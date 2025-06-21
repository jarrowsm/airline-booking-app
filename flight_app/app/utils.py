"""
Utility functions used primarily by dbprime.py.
"""

import csv
import random
import string
from datetime import datetime, date, time, timedelta, timezone
gmt = timezone.utc


def format_flight_no(flight_id: int, prefix='BA'):
    return prefix + f'{flight_id:03d}'


def int_days(days: tuple[str]) -> tuple[int]:
    """
    Converts a tuple like ('mon', 'tue') to (0, 1).
    """
    ldays = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    days_map = {day: i for i, day in enumerate(ldays)}
    return tuple(days_map[day.lower()] for day in days)


def project_dates(n_days: int, date=datetime.today().date()) -> list[date]:
    return [date + timedelta(days=i) for i in range(n_days)]


def flights_on_date(date, sched_list: list[dict]) -> list:
    return [s for s in sched_list if date.weekday() in int_days(s['days'])]


def convert_gmt_offset(offset: str) -> timezone:
    """
    Convert GMT (UTC) offset string like '+12:00' to timezone
    """
    pm = 1 if offset[0] == '+' else -1
    h_str, m_str = offset[1:].split(':')
    hours = pm * int(h_str)
    minutes = pm * int(m_str)
    return timezone(timedelta(hours=hours, minutes=minutes))


def duration_to_datetimes(
    dep_date: datetime.date,
    dep_time: str,
    duration: str,
    dep_gmt_offset: str,
) -> tuple[datetime, datetime]:
    """
    Returns departure and arrival GMT datetimes.
    """
    dep_dt = datetime.combine(
        dep_date,
        datetime.strptime(dep_time, '%H:%M').time(),
        tzinfo=convert_gmt_offset(dep_gmt_offset)
    ).astimezone(gmt)
    hours, minutes = map(int, duration.split(':'))
    arr_dt = dep_dt + timedelta(hours=hours, minutes=minutes)
    return dep_dt, arr_dt


def rand_csv_rows(csv_path, n):
    """
    Randomly sample n non-header rows.
    """
    with open(csv_path, newline='') as fin:
        rows = list(csv.reader(fin))[1:]
    return random.sample(rows, min(n, len(rows)))


def generate_booking_ref(length=6):
    poss_chars = string.digits + string.ascii_uppercase
    return ''.join(random.choices(poss_chars, k=length))


def del_dupl_vals(dict_list: list[dict], key: str):
    """
    Remove dict from list of dicts if dict[key] is duplicate.
    """
    val_count = {}
    for dict_ in dict_list:
        val = dict_[key]
        val_count[val] = val_count.get(val, 0) + 1
    return [dict_ for dict_ in dict_list if val_count[dict_[key]] == 1]


def random_instance(Model, **filters):
    qs = Model.objects.filter(**filters)
    count = qs.count()
    if count == 0:
        raise ValueError(f'{Model.__name__} with filters: {filters} is empty')
    return qs[random.randint(0, count - 1)]


def gmt_to_local(gmt_dt: datetime, offset: str) -> datetime:
    local_tz = convert_gmt_offset(offset)
    return gmt_dt.astimezone(local_tz)


def gmt_range_about(
    local_date: date,
    offset: str,
    days_fwd: int = 1,
    days_bwd: int = 0
) -> tuple[datetime, datetime]:
    """
    Create a range (default = 24h) from the start of a date and convert to GMT.
    """
    local_tz = convert_gmt_offset(offset)
    day0 = datetime.combine(local_date, time.min).replace(tzinfo=local_tz)
    start = day0 - timedelta(days=days_bwd)
    end = day0 + timedelta(days=days_fwd)
    return start.astimezone(gmt), end.astimezone(gmt)

