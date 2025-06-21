from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('destinations/', views.destinations, name='destinations'),
    path('flight_dates/', views.flight_dates, name='flight_dates'),
    path('flights/', views.flights, name='flights'),
    path('register/', views.register, name='register'),
    path('login_logout/', views.login_logout, name='login_logout'),
    path('confirm/', views.confirm, name='confirm'),
    path('bookings/', views.bookings, name='bookings'),
    path('invoice/', views.invoice, name='invoice'),
]

