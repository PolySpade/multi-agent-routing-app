import time
import schedule
from datetime import datetime
from app.services.weather_service import OpenWeatherMapService

# --- Configuration ---
# Marikina City Hall coordinates
MARIKINA_LAT = 14.6349
MARIKINA_LON = 121.1020
FETCH_INTERVAL_SECONDS = 15 # Fetch data every 15 seconds for testing

def degrees_to_cardinal(d):
    """Converts wind direction from degrees to a cardinal direction."""
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    ix = int((d + 11.25)/22.5)
    return dirs[ix % 16]

def fetch_and_print_weather_data():
    """
    The main job of our script: create a service instance, fetch data, and print it.
    """
    print(f"--- Running data collection cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

    # Initialize the service that communicates with the API
    weather_service = OpenWeatherMapService()

    # Fetch the forecast data
    weather_data = weather_service.get_forecast(MARIKINA_LAT, MARIKINA_LON)

    if weather_data and 'current' in weather_data:
        current_weather = weather_data['current']

        # --- Extract all relevant data points ---
        temp = current_weather.get('temp', 'N/A')
        feels_like = current_weather.get('feels_like', 'N/A')
        humidity = current_weather.get('humidity', 'N/A')
        pressure = current_weather.get('pressure', 'N/A')
        wind_speed = current_weather.get('wind_speed', 'N/A')
        wind_deg = current_weather.get('wind_deg', 'N/A')
        wind_direction = degrees_to_cardinal(wind_deg) if isinstance(wind_deg, (int, float)) else 'N/A'
        
        # Weather description can be a list, we take the first one
        weather_desc = 'N/A'
        if current_weather.get('weather'):
            weather_desc = current_weather['weather'][0].get('description', 'N/A').title()

        # Rainfall in the last hour (mm)
        rainfall_mm_hr = current_weather.get('rain', {}).get('1h', 0)

        # Sunrise and Sunset (convert from UNIX timestamp to readable time)
        sunrise_ts = current_weather.get('sunrise')
        sunset_ts = current_weather.get('sunset')
        sunrise_time = datetime.fromtimestamp(sunrise_ts).strftime('%H:%M:%S') if sunrise_ts else 'N/A'
        sunset_time = datetime.fromtimestamp(sunset_ts).strftime('%H:%M:%S') if sunset_ts else 'N/A'


        # --- Print the formatted data ---
        print("Current Weather Conditions for Marikina:")
        print(f"  - Condition: {weather_desc}")
        print(f"  - Temperature: {temp}°C (Feels like: {feels_like}°C)")
        print(f"  - Rainfall (last hour): {rainfall_mm_hr} mm")
        print(f"  - Humidity: {humidity}%")
        print(f"  - Wind: {wind_speed} m/s from the {wind_direction} ({wind_deg}°)")
        print(f"  - Pressure: {pressure} hPa")
        print(f"  - Sunrise: {sunrise_time} | Sunset: {sunset_time}")

    else:
        print("Failed to fetch weather data or 'current' data block is missing.")
    print("--- Cycle finished, waiting for next run... ---\n")


if __name__ == "__main__":
    print("Starting the simple data collector.")
    print(f"Data will be fetched every {FETCH_INTERVAL_SECONDS} seconds.")
    print("Press CTRL+C to stop the script.")

    # Schedule the job
    schedule.every(FETCH_INTERVAL_SECONDS).seconds.do(fetch_and_print_weather_data)

    # Run the loop
    try:
        schedule.run_all() # Run once immediately at the start
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping data collector.")
    except Exception as e:
        print(f"An error occurred: {e}")