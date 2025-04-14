import math
import folium
import requests
from django.shortcuts import render
from django.http import HttpResponse
from pydantic import BaseModel
from .models import ParkingSpace


# -----------------------------------------
# Pydantic models for clarity and reusability
# -----------------------------------------
class Point(BaseModel):
    latitude: float
    longitude: float


class Marker(BaseModel):
    point: Point
    popup: str = "Point"
    icon_color: str = "red"  # default color


# -----------------------------------------
# Helper function: generate a Folium map given a center and a list of markers.
# -----------------------------------------
def get_folium_map(center_point: Point, markers: list[Marker], zoom_level: int = 15) -> folium.Map:
    folium_map = folium.Map(location=[center_point.latitude, center_point.longitude], zoom_start=zoom_level)
    for marker in markers:
        folium.Marker(
            location=[marker.point.latitude, marker.point.longitude],
            popup=marker.popup,
            icon=folium.Icon(color=marker.icon_color)
        ).add_to(folium_map)
    return folium_map


# -----------------------------------------
# Django Views
# -----------------------------------------
def home(request):
    """Render the home page."""
    return render(request, "parking/home.html")


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) using the Haversine formula.
    """
    R = 6371  # Earth radius in kilometers.
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def generate_map(request):
    """
    Generate a Folium map centered on the user’s location. This view:
      - Adds a blue marker for the user's location.
      - Finds available parking spaces within a defined radius and adds them as green markers.
      - Builds an OSRM multi-stop route from the user’s location through all nearby parking points.
      - Displays the route as a blue polyline, with popup information on total distance and duration.
    """
    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
    except (TypeError, ValueError):
        return HttpResponse("Invalid coordinates", status=400)

    # Create a Point object for the user's location.
    user_point = Point(latitude=lat, longitude=lon)
    
    # Prepare markers list and include the user marker.
    markers: list[Marker] = []
    markers.append(Marker(point=user_point, popup="You are here", icon_color="blue"))

    # Define search radius (in km)
    radius = 100  # e.g., within 2 km radius

    # List to hold parking points to build the route
    parking_points: list[Point] = []

    # Find available parking spaces within the search radius and add markers.
    for parking in ParkingSpace.objects.filter(is_available=True):
        if parking.name == "BLACK SMOKE HAUS    ":
            distance = haversine(lat, lon, parking.latitude, parking.longitude)
            if distance <= radius:
                parking_point = Point(latitude=parking.latitude, longitude=parking.longitude)
                # Build popup with parking details.
                popup_html = (
                    f"<b>{parking.name}</b><br/>{distance:.2f} km away"
                )
                markers.append(Marker(point=parking_point, popup=popup_html, icon_color="green"))
                parking_points.append(parking_point)
    
    # Generate the Folium map with all markers.
    folium_map = get_folium_map(center_point=user_point, markers=markers, zoom_level=15)

    # Build and display a route if at least one parking space is available.
    if parking_points:
        # Build a list of points for the route starting from the user's location 
        # followed by all parking points (in the current unsorted order).
        route_points = [user_point] + parking_points

        # Build the coordinate string in "lon,lat" format separated by semicolons.
        coordinates = ';'.join([f"{pt.longitude},{pt.latitude}" for pt in route_points])

        # Build the OSRM URL.
        # In this example, we use the local OSRM backend:
        osrm_url = (
            f"http://localhost:5000/route/v1/driving/"
            f"{coordinates}?overview=full&steps=true&geometries=geojson"
        )

        # Fetch the route from OSRM.
        response = requests.get(osrm_url)
        if response.status_code == 200:
            data = response.json()
            if "routes" in data and data["routes"]:
                route = data["routes"][0]
                # OSRM returns route geometry with coordinates in [lon, lat] order.
                route_coordinates = route["geometry"]["coordinates"]
                # Swap them to [lat, lon] for Folium.
                route_coordinates = [[coord[1], coord[0]] for coord in route_coordinates]
                
                # Distance (meters) and duration (seconds)
                route_distance = route["distance"]
                route_duration = route["duration"]
                popup_text = f"Distance: {route_distance:.0f} meters<br>Duration: {route_duration:.0f} seconds"
                
                # Add the route as a blue polyline to the map.
                folium.PolyLine(
                    locations=route_coordinates, color='blue', weight=5, popup=popup_text
                ).add_to(folium_map)
        else:
            print("OSRM request failed with status code:", response.status_code)

    return HttpResponse(folium_map._repr_html_())
