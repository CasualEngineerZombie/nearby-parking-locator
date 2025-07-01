# Nearby Parking Locator

A Django-based web application that displays a dynamic map showing the user’s current location along with nearby available parking spaces. The app uses [Folium](https://python-visualization.github.io/folium/) for interactive maps and integrates with a local [OSRM](http://project-osrm.org/) backend (running in Docker) to compute driving routes. The design is kept DRY by leveraging Pydantic models and reusable helper functions.

## Demo

![Nearby Parking Locator Demo](/demo.png)

## Features

- **User Geolocation:**  
  Detects the user’s current location using the browser’s geolocation API.

- **Interactive Map with Folium:**  
  Displays an interactive map centered on the user’s location with markers indicating available parking spaces.

- **Dynamic Route Calculation:**  
  Uses OSRM backend to compute and display a multi-stop driving route from the user’s location to parking spaces within a specified radius.

- **DRY & Reusable Code:**  
  Implements helper models (using Pydantic) and utility functions for building maps and markers, ensuring code remains maintainable and DRY.

## Prerequisites

- **Python 3.8+** (or later)
- **Django 3.2+** (or later)
- **Folium**  
  Install via pip:  
  ```bash
  pip install folium
  ```

- **Requests**  
  Install via pip:  
  ```bash
  pip install requests
  ```

- **Pydantic**  
  Install via pip:  
  ```bash
  pip install pydantic
  ```

- **OSRM Backend Docker Container**  
  Ensure your OSRM service is running locally in Docker and accessible at:  
  `http://localhost:5000/`

  You can run OSRM (for example, using the [osrm-backend docker image](https://github.com/Project-OSRM/osrm-backend)) with something like:
  ```bash
  docker run -t -i -p 5000:5000 osrm/osrm-backend osrm-routed --algorithm mld /data/your-map.osrm
  ```

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/CasualEngineerZombie/nearby-parking-locator.git
   cd nearby-parking-locator
   ```

2. **Create and Activate a Virtual Environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations:**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a Superuser (Optional):**  
   This helps you to add or modify parking spaces via the Django admin.
   ```bash
   python manage.py createsuperuser
   ```

## Usage

1. **Start the OSRM Backend:**  
   Make sure your OSRM Docker container is running and accessible at `http://localhost:5000/`.

2. **Run the Django Development Server:**

   ```bash
   python manage.py runserver
   ```

3. **Access the Application:**  
   Open your web browser and navigate to [http://127.0.0.1:8000/](http://127.0.0.1:8000/).  
   Grant geolocation permission when prompted. The map will show your current location (blue marker) and, within a 2 km radius, the parking markers (green).  
   A blue polyline route connecting your location with the parking spaces is displayed based on data from the OSRM backend.  
   
4. **Django Admin:**  
   Access [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) to manage parking spaces.

## Project Structure

```
nearby-parking-locator/
├── manage.py
├── parking/                     # Django app for parking functionality
│   ├── migrations/
│   ├── templates/
│   │   └── parking/
│   │       └── home.html       # Main template that loads the map
│   ├── models.py               # ParkingSpace model definition
│   ├── views.py                # Map generation and OSRM integration views
│   └── urls.py                 # URL configuration for the parking app
├── myproject/                  # Django project folder containing settings and URL config
│   └── settings.py
└── README.md
```

The **`views.py`** includes a refactored `generate_map()` method that:
- Retrieves user geolocation from the GET parameters.
- Uses a helper `get_folium_map()` function along with Pydantic **Point** and **Marker** models to render the base map and markers.
- Collects nearby parking points and queries the OSRM backend to generate a multi-stop route.
- Displays the route using a Folium `PolyLine` along with a popup that shows the total distance and duration.

## Development

Feel free to extend the project in several ways:
- **Sorting or Filtering:**  
  Enhance parking space filtering (e.g., sort by distance, availability).
- **Improved Route Generation:**  
  Allow users to select specific parking spots or generate routes with multiple stops.
- **UI/UX Enhancements:**  
  Style the map and markers, and adjust the overall responsive design.
- **Error Handling:**  
  Add improved error handling for geolocation and OSRM request failures.
  
## Contributing

Contributions are welcome! Please fork the repository, create a new branch for your feature or bug fix, and open a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the [MIT License](LICENSE).

---

Happy coding and enjoy building your Nearby Parking Locator application!
