import math
import folium
import requests
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pydantic import BaseModel
from .models import ParkingSpace
import json


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
    radius = 2  # e.g., within 2 km radius

    # List to hold parking points to build the route
    parking_points: list[Point] = []

    # Find available parking spaces within the search radius and add markers.
    available_parkings = ParkingSpace.objects.filter(is_available=True)
    saved_spots = []
    for parking in available_parkings:
        distance = haversine(lat, lon, parking.latitude, parking.longitude)
        if distance <= radius:
            parking_point = Point(latitude=parking.latitude, longitude=parking.longitude)
            popup_html = (
                f"<b>{parking.name}</b><br/>{distance:.2f} km away"
            )
            markers.append(Marker(point=parking_point, popup=popup_html, icon_color="green"))
            parking_points.append(parking_point)
            saved_spots.append({
                "id": parking.id,
                "name": parking.name,
                "latitude": parking.latitude,
                "longitude": parking.longitude,
                "distance": round(distance, 2),
                "avatar": "/static/parking_avatar.png",
            })

    # Fetch Overpass parking spots
    overpass_spots = []
    overpass_results = fetch_overpass_parkings(lat, lon, radius)
    for spot in overpass_results:
        # Avoid duplicates: skip if very close to a saved spot
        if all(haversine(spot["latitude"], spot["longitude"], s["latitude"], s["longitude"]) > 0.03 for s in saved_spots):
            popup_html = (
                f"<div style='min-width:160px;max-width:200px;font-family:sans-serif;'>"
                f"<div style='font-weight:600;color:#1e293b;margin-bottom:2px;'>{spot['name']}</div>"
                f"<div style='font-size:12px;color:#64748b;margin-bottom:8px;'>{round(haversine(lat, lon, spot['latitude'], spot['longitude']), 2)} km away</div>"
                f"<button onclick=\"window.parent.addToMyParking({spot['latitude']}, {spot['longitude']}, '{spot['name'].replace('\'', '\\\'')}')\" "
                f"style='display:block;width:100%;margin-bottom:6px;padding:7px 0;background:linear-gradient(90deg,#6366f1,#3b82f6);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;transition:background 0.2s;' "
                f"onmouseover=\"this.style.background='#2563eb'\" onmouseout=\"this.style.background='linear-gradient(90deg,#6366f1,#3b82f6)'\">"
                f"Add to my spots</button>"
                f"<button onclick=\"window.parent.showRouteToSpot({{latitude: {spot['latitude']}, longitude: {spot['longitude']}, name: '{spot['name'].replace('\'', '\\\'')}'}})\" "
                f"style='display:block;width:100%;padding:7px 0;background:linear-gradient(90deg,#22c55e,#16a34a);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;transition:background 0.2s;' "
                f"onmouseover=\"this.style.background='#15803d'\" onmouseout=\"this.style.background='linear-gradient(90deg,#22c55e,#16a34a)'\">"
                f"Go</button>"
                f"</div>"
            )
            markers.append(Marker(
                point=Point(latitude=spot["latitude"], longitude=spot["longitude"]),
                popup=popup_html,
                icon_color="gray"
            ))
            overpass_spots.append({
                "name": spot["name"],
                "latitude": spot["latitude"],
                "longitude": spot["longitude"],
                "distance": round(haversine(lat, lon, spot["latitude"], spot["longitude"]), 2),
                "avatar": "/static/parking_avatar.png",
            })

    # Generate the Folium map with all markers.
    folium_map = get_folium_map(center_point=user_point, markers=markers, zoom_level=15)

    # Do NOT draw any route by default. Only show markers.
    # The route will be drawn when the user selects a parking spot.

    return HttpResponse(folium_map._repr_html_())


def available_parkings_api(request):
    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid coordinates"}, status=400)

    radius = 2  # km
    available_parkings = ParkingSpace.objects.filter(is_available=True)
    saved_spots = []
    for parking in available_parkings:
        distance = haversine(lat, lon, parking.latitude, parking.longitude)
        if distance <= radius:
            saved_spots.append({
                "id": parking.id,
                "name": parking.name,
                "latitude": parking.latitude,
                "longitude": parking.longitude,
                "distance": round(distance, 2),
                "avatar": "/static/parking_avatar.png",
            })

    # Overpass
    overpass_spots = []
    overpass_results = fetch_overpass_parkings(lat, lon, radius)
    for spot in overpass_results:
        if all(haversine(spot["latitude"], spot["longitude"], s["latitude"], s["longitude"]) > 0.03 for s in saved_spots):
            overpass_spots.append({
                "name": spot["name"],
                "latitude": spot["latitude"],
                "longitude": spot["longitude"],
                "distance": round(haversine(lat, lon, spot["latitude"], spot["longitude"]), 2),
                "avatar": "/static/parking_avatar.png",
            })

    return JsonResponse({
        "saved_spots": saved_spots,
        "other_spots": overpass_spots
    })


def single_route_map(request):
    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
        dest_lat = float(request.GET.get('dest_lat'))
        dest_lon = float(request.GET.get('dest_lon'))
    except (TypeError, ValueError):
        return HttpResponse("Invalid coordinates", status=400)

    user_point = Point(latitude=lat, longitude=lon)
    dest_point = Point(latitude=dest_lat, longitude=dest_lon)
    markers = [
        Marker(point=user_point, popup="You are here", icon_color="blue"),
        Marker(point=dest_point, popup="Selected Parking", icon_color="green"),
    ]
    folium_map = get_folium_map(center_point=user_point, markers=markers, zoom_level=15)

    coordinates = f"{lon},{lat};{dest_lon},{dest_lat}"
    osrm_url = (
        f"https://parkee-osrm-backend.fly.dev/route/v1/driving/"
        f"{coordinates}?overview=full&steps=true&geometries=geojson"
    )
    response = requests.get(osrm_url)
    if response.status_code == 200:
        data = response.json()
        if "routes" in data and data["routes"]:
            route = data["routes"][0]
            route_coordinates = [[coord[1], coord[0]] for coord in route["geometry"]["coordinates"]]
            route_distance = route["distance"]
            route_duration = route["duration"]
            popup_text = f"Distance: {route_distance:.0f} meters<br>Duration: {route_duration:.0f} seconds"
            folium.PolyLine(
                locations=route_coordinates, color='blue', weight=5, popup=popup_text
            ).add_to(folium_map)
    return HttpResponse(folium_map._repr_html_())


@csrf_exempt
def add_parking(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        name = data.get("name", "Unnamed Parking")
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)
    # Prevent duplicates (within ~30m)
    from .models import ParkingSpace
    for p in ParkingSpace.objects.all():
        if abs(p.latitude - latitude) < 0.0003 and abs(p.longitude - longitude) < 0.0003:
            return JsonResponse({"error": "Parking spot already saved."}, status=400)
    ParkingSpace.objects.create(name=name, latitude=latitude, longitude=longitude, is_available=True)
    return JsonResponse({"success": True})


@csrf_exempt
def update_parking_name(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        parking_id = int(data["id"])
        new_name = data["name"].strip()
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)
    from .models import ParkingSpace
    try:
        parking = ParkingSpace.objects.get(id=parking_id)
        parking.name = new_name
        parking.save()
        return JsonResponse({"success": True})
    except ParkingSpace.DoesNotExist:
        return JsonResponse({"error": "Parking spot not found"}, status=404)


@csrf_exempt
def remove_parking(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        parking_id = int(data["id"])
    except Exception:
        return JsonResponse({"error": "Invalid data"}, status=400)
    from .models import ParkingSpace
    try:
        parking = ParkingSpace.objects.get(id=parking_id)
        parking.delete()
        return JsonResponse({"success": True})
    except ParkingSpace.DoesNotExist:
        return JsonResponse({"error": "Parking spot not found"}, status=404)


def fetch_overpass_parkings(lat, lon, radius_km=2):
    # Overpass QL: find amenity=parking within radius
    radius_m = int(radius_km * 1000)
    query = f"""
    [out:json];
    (
      node["amenity"="parking"](around:{radius_m},{lat},{lon});
      way["amenity"="parking"](around:{radius_m},{lat},{lon});
      relation["amenity"="parking"](around:{radius_m},{lat},{lon});
    );
    out center 20;
    """
    url = "https://overpass-api.de/api/interpreter"
    try:
        resp = requests.post(url, data={'data': query}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            spots = []
            for el in data.get("elements", []):
                if el["type"] == "node":
                    spots.append({
                        "name": el.get("tags", {}).get("name", "Unnamed Parking"),
                        "latitude": el["lat"],
                        "longitude": el["lon"],
                    })
                elif "center" in el:
                    spots.append({
                        "name": el.get("tags", {}).get("name", "Unnamed Parking"),
                        "latitude": el["center"]["lat"],
                        "longitude": el["center"]["lon"],
                    })
            return spots
    except Exception as e:
        print("Overpass error:", e)
    return []
