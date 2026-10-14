"""Weather MCP Server — Remote MCP Server for Lab 04.

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720
"""

from typing import Any
import asyncio
import httpx
import os
import sys
from mcp.server.fastmcp import FastMCP

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Initialize FastMCP server
port = int(os.getenv("PORT", 8085))
mcp = FastMCP("weather", host="0.0.0.0", port=port)

# Constants
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
USER_AGENT = "weather-app/1.0"

# Get API key from environment variable
API_KEY = os.getenv("WEATHERAPI_KEY")

# Fallback mock data when WeatherAPI key is not configured or network request fails
_MOCK_LOCATIONS: dict[str, dict[str, Any]] = {
    "hanoi": {
        "location": {"name": "Hanoi", "region": "Ha Noi", "country": "Vietnam"},
        "current": {
            "temp_c": 29.0, "temp_f": 84.2, "feelslike_c": 32.0, "feelslike_f": 89.6,
            "condition": {"text": "Partly cloudy"}, "humidity": 82,
            "wind_kph": 12.0, "wind_mph": 7.5, "wind_dir": "SE",
            "pressure_mb": 1010.0, "uv": 6.0, "vis_km": 10.0,
            "last_updated": "2026-10-14 18:00"
        },
        "forecast": [
            {"date": "2026-10-15", "day": {"maxtemp_c": 31.0, "maxtemp_f": 87.8, "mintemp_c": 24.0, "mintemp_f": 75.2, "condition": {"text": "Sunny"}, "daily_chance_of_rain": 10, "maxwind_kph": 15.0, "uv": 7.0}},
            {"date": "2026-10-16", "day": {"maxtemp_c": 30.0, "maxtemp_f": 86.0, "mintemp_c": 23.0, "mintemp_f": 73.4, "condition": {"text": "Patchy rain"}, "daily_chance_of_rain": 60, "maxwind_kph": 18.0, "uv": 5.0}},
            {"date": "2026-10-17", "day": {"maxtemp_c": 28.0, "maxtemp_f": 82.4, "mintemp_c": 22.0, "mintemp_f": 71.6, "condition": {"text": "Light rain"}, "daily_chance_of_rain": 75, "maxwind_kph": 14.0, "uv": 4.0}},
        ]
    },
    "danang": {
        "location": {"name": "Danang", "region": "Da Nang", "country": "Vietnam"},
        "current": {
            "temp_c": 30.0, "temp_f": 86.0, "feelslike_c": 34.0, "feelslike_f": 93.2,
            "condition": {"text": "Partly cloudy"}, "humidity": 78,
            "wind_kph": 10.0, "wind_mph": 6.2, "wind_dir": "E",
            "pressure_mb": 1011.0, "uv": 7.0, "vis_km": 10.0,
            "last_updated": "2026-10-14 18:00"
        },
        "forecast": [
            {"date": "2026-10-15", "day": {"maxtemp_c": 32.0, "maxtemp_f": 89.6, "mintemp_c": 25.0, "mintemp_f": 77.0, "condition": {"text": "Sunny"}, "daily_chance_of_rain": 15, "maxwind_kph": 12.0, "uv": 8.0}},
            {"date": "2026-10-16", "day": {"maxtemp_c": 31.0, "maxtemp_f": 87.8, "mintemp_c": 24.0, "mintemp_f": 75.2, "condition": {"text": "Moderate rain"}, "daily_chance_of_rain": 70, "maxwind_kph": 20.0, "uv": 4.0}},
            {"date": "2026-10-17", "day": {"maxtemp_c": 29.0, "maxtemp_f": 84.2, "mintemp_c": 23.0, "mintemp_f": 73.4, "condition": {"text": "Cloudy"}, "daily_chance_of_rain": 30, "maxwind_kph": 16.0, "uv": 6.0}},
        ]
    },
    "haiphong": {
        "location": {"name": "Haiphong", "region": "Hai Phong", "country": "Vietnam"},
        "current": {
            "temp_c": 33.0, "temp_f": 91.4, "feelslike_c": 37.0, "feelslike_f": 98.6,
            "condition": {"text": "Heavy rain"}, "humidity": 75,
            "wind_kph": 15.0, "wind_mph": 9.3, "wind_dir": "SW",
            "pressure_mb": 1009.0, "uv": 5.0, "vis_km": 8.0,
            "last_updated": "2026-10-14 18:00"
        },
        "forecast": [
            {"date": "2026-10-15", "day": {"maxtemp_c": 30.0, "maxtemp_f": 86.0, "mintemp_c": 24.0, "mintemp_f": 75.2, "condition": {"text": "Rain"}, "daily_chance_of_rain": 80, "maxwind_kph": 18.0, "uv": 4.0}},
            {"date": "2026-10-16", "day": {"maxtemp_c": 29.0, "maxtemp_f": 84.2, "mintemp_c": 23.0, "mintemp_f": 73.4, "condition": {"text": "Cloudy"}, "daily_chance_of_rain": 40, "maxwind_kph": 14.0, "uv": 5.0}},
            {"date": "2026-10-17", "day": {"maxtemp_c": 31.0, "maxtemp_f": 87.8, "mintemp_c": 25.0, "mintemp_f": 77.0, "condition": {"text": "Sunny"}, "daily_chance_of_rain": 10, "maxwind_kph": 12.0, "uv": 7.0}},
        ]
    },
    "brisbane": {
        "location": {"name": "Brisbane", "region": "Queensland", "country": "Australia"},
        "current": {
            "temp_c": 24.0, "temp_f": 75.2, "feelslike_c": 24.5, "feelslike_f": 76.1,
            "condition": {"text": "Clear"}, "humidity": 65,
            "wind_kph": 18.0, "wind_mph": 11.2, "wind_dir": "ENE",
            "pressure_mb": 1018.0, "uv": 8.0, "vis_km": 10.0,
            "last_updated": "2026-10-14 18:00"
        },
        "forecast": [
            {"date": "2026-10-15", "day": {"maxtemp_c": 26.0, "maxtemp_f": 78.8, "mintemp_c": 16.0, "mintemp_f": 60.8, "condition": {"text": "Sunny"}, "daily_chance_of_rain": 5, "maxwind_kph": 20.0, "uv": 9.0}},
            {"date": "2026-10-16", "day": {"maxtemp_c": 27.0, "maxtemp_f": 80.6, "mintemp_c": 17.0, "mintemp_f": 62.6, "condition": {"text": "Partly cloudy"}, "daily_chance_of_rain": 10, "maxwind_kph": 22.0, "uv": 8.0}},
            {"date": "2026-10-17", "day": {"maxtemp_c": 25.0, "maxtemp_f": 77.0, "mintemp_c": 18.0, "mintemp_f": 64.4, "condition": {"text": "Showers"}, "daily_chance_of_rain": 45, "maxwind_kph": 25.0, "uv": 6.0}},
        ]
    },
    "sydney": {
        "location": {"name": "Sydney", "region": "New South Wales", "country": "Australia"},
        "current": {
            "temp_c": 21.0, "temp_f": 69.8, "feelslike_c": 21.0, "feelslike_f": 69.8,
            "condition": {"text": "Mostly Sunny"}, "humidity": 60,
            "wind_kph": 20.0, "wind_mph": 12.4, "wind_dir": "S",
            "pressure_mb": 1020.0, "uv": 7.0, "vis_km": 10.0,
            "last_updated": "2026-10-14 18:00"
        },
        "forecast": [
            {"date": "2026-10-15", "day": {"maxtemp_c": 23.0, "maxtemp_f": 73.4, "mintemp_c": 14.0, "mintemp_f": 57.2, "condition": {"text": "Sunny"}, "daily_chance_of_rain": 5, "maxwind_kph": 18.0, "uv": 8.0}},
            {"date": "2026-10-16", "day": {"maxtemp_c": 24.0, "maxtemp_f": 75.2, "mintemp_c": 15.0, "mintemp_f": 59.0, "condition": {"text": "Fine"}, "daily_chance_of_rain": 5, "maxwind_kph": 15.0, "uv": 8.0}},
            {"date": "2026-10-17", "day": {"maxtemp_c": 20.0, "maxtemp_f": 68.0, "mintemp_c": 13.0, "mintemp_f": 55.4, "condition": {"text": "Cloudy with drizzle"}, "daily_chance_of_rain": 50, "maxwind_kph": 24.0, "uv": 5.0}},
        ]
    },
}

def _get_mock_fallback(city: str) -> dict[str, Any]:
    """Provide realistic mock fallback data for any city."""
    normalized = city.strip().lower()
    if normalized in _MOCK_LOCATIONS:
        return _MOCK_LOCATIONS[normalized]
    
    # Generic mock for unknown city
    clean_name = city.strip().title()
    return {
        "location": {"name": clean_name, "region": "Region", "country": "World"},
        "current": {
            "temp_c": 26.0, "temp_f": 78.8, "feelslike_c": 27.0, "feelslike_f": 80.6,
            "condition": {"text": "Partly Cloudy"}, "humidity": 70,
            "wind_kph": 14.0, "wind_mph": 8.7, "wind_dir": "NE",
            "pressure_mb": 1013.0, "uv": 5.0, "vis_km": 10.0,
            "last_updated": "2026-10-14 18:00"
        },
        "forecast": [
            {"date": "2026-10-15", "day": {"maxtemp_c": 28.0, "maxtemp_f": 82.4, "mintemp_c": 20.0, "mintemp_f": 68.0, "condition": {"text": "Sunny"}, "daily_chance_of_rain": 10, "maxwind_kph": 15.0, "uv": 6.0}},
            {"date": "2026-10-16", "day": {"maxtemp_c": 27.0, "maxtemp_f": 80.6, "mintemp_c": 19.0, "mintemp_f": 66.2, "condition": {"text": "Scattered Clouds"}, "daily_chance_of_rain": 25, "maxwind_kph": 16.0, "uv": 6.0}},
            {"date": "2026-10-17", "day": {"maxtemp_c": 25.0, "maxtemp_f": 77.0, "mintemp_c": 18.0, "mintemp_f": 64.4, "condition": {"text": "Light Rain"}, "daily_chance_of_rain": 60, "maxwind_kph": 18.0, "uv": 4.0}},
        ]
    }


async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to the WeatherAPI with proper error handling."""
    if not API_KEY:
        return None
        
    headers = {
        "User-Agent": USER_AGENT,
    }
    params["key"] = API_KEY
    url = f"{WEATHERAPI_BASE}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Request Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    params = {
        "q": city,
        "aqi": "no"
    }
    
    data = await make_weather_request("current.json", params)
    demo_tag = ""

    if not data:
        # Fallback to realistic mock data so server works seamlessly in demo/lab
        mock_info = _get_mock_fallback(city)
        current = mock_info["current"]
        location = mock_info["location"]
        demo_tag = "\n*(Demo data mode — configure WEATHERAPI_KEY for live data)*\n"
    else:
        current = data["current"]
        location = data["location"]
    
    return f"""
Current Weather for {location['name']}, {location['region']}, {location['country']}:
{demo_tag}
Temperature: {current['temp_c']}°C ({current['temp_f']}°F)
Feels like: {current['feelslike_c']}°C ({current['feelslike_f']}°F)
Condition: {current['condition']['text']}
Humidity: {current['humidity']}%
Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}
Pressure: {current['pressure_mb']} mb
UV Index: {current['uv']}
Visibility: {current['vis_km']} km

Last updated: {current['last_updated']}
"""


@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-3 for free tier, max 10 for paid)
    """
    days = min(max(days, 1), 3)
    
    params = {
        "q": city,
        "days": str(days),
        "aqi": "no",
        "alerts": "no"
    }
    
    data = await make_weather_request("forecast.json", params)
    demo_tag = ""

    if not data:
        mock_info = _get_mock_fallback(city)
        location = mock_info["location"]
        forecast_days = mock_info["forecast"][:days]
        demo_tag = " *(Demo mode)*"
    else:
        location = data["location"]
        forecast_days = data["forecast"]["forecastday"][:days]
    
    forecasts = []
    forecasts.append(f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}{demo_tag}:")
    
    for day in forecast_days:
        day_data = day["day"]
        date = day["date"]
        
        forecast = f"""
{date}:
High: {day_data['maxtemp_c']}°C ({day_data['maxtemp_f']}°F)
Low: {day_data['mintemp_c']}°C ({day_data['mintemp_f']}°F)
Condition: {day_data['condition']['text']}
Chance of Rain: {day_data['daily_chance_of_rain']}%
Max Wind: {day_data['maxwind_kph']} km/h
UV Index: {day_data['uv']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    return "✅ Weather MCP Server is running! Ready to provide weather data for Australian cities, Vietnam cities, and worldwide."


print("✅ MCP server initialized with Streamable HTTP transport")
print("🔧 Available tools: get_current_weather, get_forecast, health_check")

if __name__ == "__main__":
    if "--stdio" in sys.argv:
        print("Starting FastMCP server in stdio mode for local client", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        print(f"🚀 Starting MCP server on http://0.0.0.0:{port}/mcp")
        mcp.run(transport="streamable-http")