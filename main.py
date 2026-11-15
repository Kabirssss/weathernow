from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

app = FastAPI(title="Weather API", description="A beginner-friendly current weather API.")

STATIC_DIR = Path(__file__).parent / "static"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


class Location(BaseModel):
    name: str
    country: str | None = None
    latitude: float
    longitude: float


class GeocodingResponse(BaseModel):
    results: list[Location] = Field(default_factory=list)


class CurrentConditions(BaseModel):
    temperature_2m: float
    apparent_temperature: float
    relative_humidity_2m: int
    wind_speed_10m: float
    weather_code: int
    is_day: int


class ForecastResponse(BaseModel):
    timezone: str
    current: CurrentConditions


class WeatherResponse(BaseModel):
    city: str
    country: str | None
    timezone: str
    temperature_c: float
    feels_like_c: float
    humidity_percent: int
    wind_speed_kmh: float
    weather_code: int
    description: str
    is_day: bool


def describe_weather(code: int) -> str:
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return descriptions.get(code, "Unknown conditions")


async def fetch_weather(city: str) -> WeatherResponse:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            location_response = await client.get(
                GEOCODING_URL,
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            location_response.raise_for_status()
            location_data = location_response.json()
            location = GeocodingResponse.model_validate(location_data).results
        except (httpx.HTTPError, ValueError, ValidationError) as error:
            raise HTTPException(
                status_code=502,
                detail="The weather provider could not look up that city.",
            ) from error

        if not location:
            raise HTTPException(status_code=404, detail=f"No city found for '{city}'.")

        place = location[0]

        try:
            forecast_response = await client.get(
                FORECAST_URL,
                params={
                    "latitude": place.latitude,
                    "longitude": place.longitude,
                    "current": (
                        "temperature_2m,apparent_temperature,relative_humidity_2m,"
                        "wind_speed_10m,weather_code,is_day"
                    ),
                    "wind_speed_unit": "kmh",
                    "timezone": "auto",
                },
            )
            forecast_response.raise_for_status()
            forecast_data = ForecastResponse.model_validate(forecast_response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as error:
            raise HTTPException(
                status_code=502,
                detail="The weather provider returned an invalid forecast.",
            ) from error

    current = forecast_data.current
    return WeatherResponse(
        city=place.name,
        country=place.country,
        timezone=forecast_data.timezone,
        temperature_c=current.temperature_2m,
        feels_like_c=current.apparent_temperature,
        humidity_percent=current.relative_humidity_2m,
        wind_speed_kmh=current.wind_speed_10m,
        weather_code=current.weather_code,
        description=describe_weather(current.weather_code),
        is_day=current.is_day == 1,
    )


@app.get("/api/weather", response_model=WeatherResponse)
async def get_weather(
    city: Annotated[str, Query(min_length=1, max_length=100)],
) -> WeatherResponse:
    city = city.strip()
    if not city:
        raise HTTPException(status_code=422, detail="City must not be blank.")

    return await fetch_weather(city)
