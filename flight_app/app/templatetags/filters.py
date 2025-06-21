"""
Filters to help isolate logic for template rendering.
"""

from django import template
from django.utils.safestring import mark_safe
from datetime import datetime, date, timezone
gmt = timezone.utc

register = template.Library()


@register.filter
def format_duration(duration):
    if not duration:
        return ''

    total = int(duration.total_seconds())
    h, r = divmod(total, 3600)
    m = r // 60
    return f"{h}h {m}m" if h else f"{m}m"


@register.filter
def local_dt(local_dt, strformat='%b %-d, %Y, %-I:%M %p'):
    """
    Format while preventing Django from converting to UTC.
    """
    return local_dt.strftime(strformat)


@register.filter
def local_d(local_d, strformat='%b %-d, %Y'):
    return local_d.strftime(strformat)


@register.filter
def local_t(local_t, strformat='%-I:%M %p'):
    return local_t.strftime(strformat)


@register.filter
def form_css(field, classes):
    """
    Add CSS classes to a form field outside of forms.py.
    """
    current = field.field.widget.attrs.get('class', '').split()
    new = classes.split()

    for c in new:
        if c not in current:
            current.append(c)

    field.field.widget.attrs['class'] = ' '.join(current)

    return field


@register.filter
def gt(a, b):
    return a > b


@register.filter
def multiply(a, b):
    return a * b


@register.filter
def date_before_now(d: date):
    return d < datetime.now(gmt).date()


@register.filter
def route_img_path(orig_icao, dest_icao):
    """
    Find the image path independent of whether NZNE is origin or destination
    """
    icao = dest_icao if orig_icao == 'NZNE' else orig_icao
    return f'images/{icao}.gif'


@register.filter
def flights_nav_head(search):
    """
    Format nav_head in search/ based on the query parameters
    """
    if search.get('return_date'):
        arrow = '<i class="bi-arrow-left-right" style="transform: scaleX(-1); display: inline-block;"></i>'
    else:
        arrow = '<i class="bi-arrow-right"></i>'
    origin = search['origin'].region
    destination = search['destination'].region
    return mark_safe(f'{origin} {arrow} {destination}')

