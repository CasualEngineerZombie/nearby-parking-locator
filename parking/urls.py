from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('map/', views.generate_map, name="generate_map"),
    path('api/available_parkings/', views.available_parkings_api, name='available_parkings_api'),
    path('map/single_route/', views.single_route_map, name='single_route_map'),
    path('api/add_parking/', views.add_parking, name='add_parking'),
    path('api/update_parking_name/', views.update_parking_name, name='update_parking_name'),
    path('api/remove_parking/', views.remove_parking, name='remove_parking'),
]
