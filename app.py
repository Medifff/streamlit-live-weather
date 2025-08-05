import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# Set the page configuration
st.set_page_config(layout="wide", page_title="Live Weather Dashboard")

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅️", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    56: "🌨️", 57: "🌨️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    66: "🌨️", 67: "🌨️",
    71: "❄️", 73: "❄️", 75: "❄️",
    77: "❄️",
    80: "🌧️", 81: "🌧️", 82: "🌧️",
    85: "❄️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️"
}

def get_weather_icon(weather_code):
    """Returns an emoji icon for a given WMO weather code."""
    return WEATHER_ICONS.get(weather_code, "❓")

@st.cache_data(ttl=3600)
def get_coordinates(city_name):
    """Fetches latitude and longitude for a given city name."""
    params = {"name": city_name, "count": 1}
    try:
        response = requests.get(GEOCODING_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            location = data["results"][0]
            return location["latitude"], location["longitude"], location.get("country", "")
        else:
            return None, None, None
    except requests.exceptions.RequestException as e:
        st.error(f"Error during geocoding: {e}")
        return None, None, None

@st.cache_data(ttl=600)
def fetch_weather_data(latitude, longitude, is_historical=False):
    """Fetches weather data from the Open-Meteo API for given coordinates."""
    today = datetime.utcnow()
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
    }
    
    if is_historical:
        params["start_date"] = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        params["end_date"] = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        params["daily"] = "temperature_2m_max,temperature_2m_min,weather_code"
    else:
        params["current"] = "temperature_2m,weather_code,precipitation_probability,wind_speed_10m"
        params["hourly"] = "temperature_2m,precipitation_probability,wind_speed_10m"
        params["forecast_days"] = 1

    try:
        response = requests.get(WEATHER_API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching weather data: {e}")
        return None

# --- Main App ---
st.title("Live Weather Forecast")

city = st.text_input("Enter a city name:", "Lviv")

if city:
    lat, lon, country = get_coordinates(city)

    if lat is not None and lon is not None:
        st.subheader(f"Weather for {city.title()}, {country}")
        
        forecast_data = fetch_weather_data(lat, lon)
        historical_data = fetch_weather_data(lat, lon, is_historical=True)

        ## UI REFINEMENT: Create tabs to organize the content.
        tab1, tab2, tab3 = st.tabs(["Current Conditions", "Hourly Forecast", "Historical Data"])

        with tab1:
            if forecast_data:
                current_weather = forecast_data.get("current", {})
                current_temp = current_weather.get("temperature_2m")
                current_weather_code = current_weather.get("weather_code")
                weather_icon = get_weather_icon(current_weather_code)
                precip_prob = current_weather.get("precipitation_probability")
                wind_speed = current_weather.get("wind_speed_10m")

                if current_temp is not None:
                    col1, col2, col3 = st.columns(3)
                    col1.metric(label=f"Temperature {weather_icon}", value=f"{current_temp}°C")
                    col2.metric(label="Wind Speed 💨", value=f"{wind_speed} km/h")
                    col3.metric(label="Precipitation Chance 💧", value=f"{precip_prob}%")
                else:
                    st.warning("Could not retrieve current conditions.")
            else:
                st.warning("Could not retrieve forecast data.")

        with tab2:
            if forecast_data:
                hourly_data = forecast_data.get("hourly", {})
                if hourly_data and 'time' in hourly_data:
                    st.subheader("Forecast for the Next 24 Hours")
                    hourly_df = pd.DataFrame(hourly_data)
                    hourly_df['time'] = pd.to_datetime(hourly_df['time'])
                    hourly_df.set_index('time', inplace=True)
                    st.line_chart(hourly_df)
                    with st.expander("View Hourly Data Table"):
                        st.dataframe(hourly_df)
                else:
                    st.warning("Could not retrieve hourly forecast data.")
            else:
                st.warning("Could not retrieve forecast data.")

        with tab3:
            if historical_data:
                daily_data = historical_data.get("daily", {})
                if daily_data and 'time' in daily_data:
                    st.subheader("Weather for the Last 7 Days")
                    historical_df = pd.DataFrame(daily_data)
                    historical_df['time'] = pd.to_datetime(historical_df['time'])
                    historical_df.set_index('time', inplace=True)
                    
                    temp_df = historical_df[['temperature_2m_max', 'temperature_2m_min']]
                    temp_df.rename(columns={'temperature_2m_max': 'Max Temp (°C)', 'temperature_2m_min': 'Min Temp (°C)'}, inplace=True)
                    
                    st.bar_chart(temp_df)
                    with st.expander("View Historical Data Table"):
                        st.dataframe(historical_df)
                else:
                    st.warning("Could not retrieve historical data.")
            else:
                st.warning("Could not retrieve historical data.")

    else:
        st.error(f"Could not find coordinates for '{city}'. Please check the spelling or try a different city.")
