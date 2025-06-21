from django.db import models
from app.utils import gmt_to_local
from datetime import datetime, timezone
gmt = timezone.utc
from django.utils.timezone import now


class Aircraft(models.Model):
    name = models.CharField(max_length=50, primary_key=True)
    brand = models.CharField(max_length=50)
    max_seats = models.IntegerField()

    class Meta:
        db_table = 'Aircraft'


class Airport(models.Model):
    icao = models.CharField(max_length=4, primary_key=True)
    name = models.CharField(max_length=100)
    region = models.CharField(max_length=50)
    gmt_offset = models.CharField(max_length=6, default='+12:00')  # [+/-]HH:MM

    class Meta:
        db_table = 'Airport'


class Schedule(models.Model):
    flight_no = models.CharField(max_length=6)
    dep_dt = models.DateTimeField()
    arr_dt = models.DateTimeField()
    seats_avail = models.IntegerField()
    aircraft =  models.ForeignKey(
        Aircraft,
        related_name='aircraft',
        on_delete=models.CASCADE,
    )
    dep_icao = models.ForeignKey(
        Airport,
        related_name='dep_icao',
        on_delete=models.CASCADE
    )
    arr_icao = models.ForeignKey(
        Airport,
        related_name='arr_icao',
        on_delete=models.CASCADE
    )
    base_price = models.FloatField()

    @property
    def duration(self):
        return self.arr_dt - self.dep_dt

    @property
    def current_price(self):
        """
        Dynamic price:
         - 50% weighted seat ratio
         - +1.5% for each day within 28 days
         - base price 3 days before departure
         - cap of +40% over base price
        """
        n_days = (self.dep_dt - datetime.now(gmt)).days

        if n_days <= 3:
            return self.base_price

        days = max(0, 28 - n_days)
        max_seats = self.aircraft.max_seats 
        seat_ratio = (max_seats - self.seats_avail) / max_seats
        pct = min(0.015 * days + 0.5 * seat_ratio, 0.4)
        mult = 1 + pct
        return round(self.base_price * mult, 2)

    @property
    def dep_dt_local(self):
        return gmt_to_local(self.dep_dt, self.dep_icao.gmt_offset)

    @property
    def arr_dt_local(self):
        return gmt_to_local(self.arr_dt, self.arr_icao.gmt_offset)

    @property
    def next_day_tag(self):
        return '(next day)' if self.arr_dt_local.date() > self.dep_dt_local.date() else ''

    class Meta:
        db_table = 'Schedule'


class Customer(models.Model):
    title = models.CharField(max_length=10)
    fname = models.CharField(max_length=50)
    lname = models.CharField(max_length=50)
    sex = models.CharField(max_length=1)
    email = models.EmailField(max_length=254, unique=True)
    
    class Meta:
        db_table = 'Customer'


class Booking(models.Model):
    ref = models.CharField(max_length=6, primary_key=True)
    tickets = models.IntegerField()
    customer = models.ForeignKey(
        Customer,
        related_name='customer',
        on_delete=models.CASCADE
    )
    depart_schedule = models.ForeignKey(
        Schedule,
        related_name='depart_schedule',
        on_delete=models.CASCADE
    )
    return_schedule = models.ForeignKey(
        Schedule,
        related_name='return_schedule',
        on_delete=models.CASCADE,
        null=True
    )
    depart_price = models.FloatField()
    return_price = models.FloatField(null=True)
    created_at = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-created_at']
        db_table = 'Booking'

