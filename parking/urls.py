from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('map/', views.generate_map, name="generate_map"),
]
