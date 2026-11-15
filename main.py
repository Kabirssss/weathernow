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


class DailyConditions(BaseModel):
    time: list[str]
    weather_code: list[int]
    temperature_2m_max: list[float]
    temperature_2m_min: list[float]


class ForecastResponse(BaseModel):
    timezone: str
    current: CurrentConditions
    daily: DailyConditions


class ForecastDay(BaseModel):
    date: str
    weather_code: int
    description: str
    high_c: float
    low_c: float


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
    forecast: list[ForecastDay]
    trend: list[ForecastDay]


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


async def search_locations(city: str, count: int = 5) -> list[Location]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                GEOCODING_URL,
                params={
                    "name": city,
                    "count": count,
                    "language": "en",
                    "format": "json",
                },
            )
            response.raise_for_status()
            return GeocodingResponse.model_validate(response.json()).results
        except (httpx.HTTPError, ValueError, ValidationError) as error:
            raise HTTPException(
                status_code=502,
                detail="The weather provider could not look up that city.",
            ) from error


async def fetch_weather_for_location(place: Location) -> WeatherResponse:
    async with httpx.AsyncClient(timeout=10.0) as client:
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
                    "daily": (
                        "weather_code,temperature_2m_max,temperature_2m_min"
                    ),
                    "forecast_days": 10,
                    "wind_speed_unit": "kmh",
                    "timezone": "auto",
                },
            )
            forecast_response.raise_for_status()
            forecast_data = ForecastResponse.model_validate(forecast_response.json())

            daily_forecast = [
                ForecastDay(
                    date=date,
                    weather_code=code,
                    description=describe_weather(code),
                    high_c=high,
                    low_c=low,
                )
                for date, code, high, low in zip(
                    forecast_data.daily.time,
                    forecast_data.daily.weather_code,
                    forecast_data.daily.temperature_2m_max,
                    forecast_data.daily.temperature_2m_min,
                    strict=True,
                )
            ]
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
        forecast=daily_forecast[:5],
        trend=daily_forecast,
    )


async def fetch_weather(city: str) -> WeatherResponse:
    locations = await search_locations(city, count=1)
    if not locations:
        raise HTTPException(status_code=404, detail=f"No city found for '{city}'.")
    return await fetch_weather_for_location(locations[0])


async def fetch_weather_for_coordinates(
    latitude: float, longitude: float
) -> WeatherResponse:
    place = Location(
        name="Your location",
        latitude=latitude,
        longitude=longitude,
    )
    return await fetch_weather_for_location(place)


@app.get("/api/cities", response_model=list[Location])
async def get_city_suggestions(
    name: Annotated[str, Query(min_length=2, max_length=100)],
) -> list[Location]:
    name = name.strip()
    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Enter at least two characters to search for a city.",
        )
    return await search_locations(name)


@app.get("/api/weather", response_model=WeatherResponse)
async def get_weather(
    city: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> WeatherResponse:
    if latitude is not None or longitude is not None:
        if latitude is None or longitude is None or city is not None:
            raise HTTPException(
                status_code=422,
                detail="Provide both latitude and longitude, without a city name.",
            )
        return await fetch_weather_for_coordinates(latitude, longitude)

    if city is None:
        raise HTTPException(
            status_code=422,
            detail="Provide a city name or your latitude and longitude.",
        )

    city = city.strip()
    if not city:
        raise HTTPException(status_code=422, detail="City must not be blank.")

    return await fetch_weather(city)
