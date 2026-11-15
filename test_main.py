import asyncio

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def sample_weather(city: str = "London") -> main.WeatherResponse:
    return main.WeatherResponse(
        city=city,
        country="United Kingdom" if city != "Your location" else None,
        timezone="Europe/London",
        temperature_c=18.5,
        feels_like_c=18.0,
        humidity_percent=62,
        wind_speed_kmh=12.0,
        weather_code=2,
        description="Partly cloudy",
        is_day=True,
        forecast=[
            main.ForecastDay(
                date="2026-11-15",
                weather_code=2,
                description="Partly cloudy",
                high_c=19.0,
                low_c=12.0,
            )
        ],
        trend=[
            main.ForecastDay(
                date="2026-11-15",
                weather_code=2,
                description="Partly cloudy",
                high_c=19.0,
                low_c=12.0,
            ),
            main.ForecastDay(
                date="2026-11-16",
                weather_code=3,
                description="Overcast",
                high_c=17.0,
                low_c=11.0,
            ),
        ],
    )


def test_home_page_is_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Weather, wherever you are." in response.text
    assert "10-day temperature trend" in response.text
    assert 'id="forecast-list"' not in response.text


def test_frontend_assets_are_served() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "api/weather" in response.text
    assert "trend-date-marker" in response.text
    assert "TODAY" in response.text
    assert "trend-tooltip" in response.text


def test_weather_endpoint_returns_weather(monkeypatch) -> None:
    async def fake_fetch_weather(city: str) -> main.WeatherResponse:
        assert city == "London"
        return sample_weather(city)

    monkeypatch.setattr(main, "fetch_weather", fake_fetch_weather)

    response = client.get("/api/weather", params={"city": "London"})

    assert response.status_code == 200
    assert response.json() == {
        "city": "London",
        "country": "United Kingdom",
        "timezone": "Europe/London",
        "temperature_c": 18.5,
        "feels_like_c": 18.0,
        "humidity_percent": 62,
        "wind_speed_kmh": 12.0,
        "weather_code": 2,
        "description": "Partly cloudy",
        "is_day": True,
        "forecast": [
            {
                "date": "2026-11-15",
                "weather_code": 2,
                "description": "Partly cloudy",
                "high_c": 19.0,
                "low_c": 12.0,
            }
        ],
        "trend": [
            {
                "date": "2026-11-15",
                "weather_code": 2,
                "description": "Partly cloudy",
                "high_c": 19.0,
                "low_c": 12.0,
            },
            {
                "date": "2026-11-16",
                "weather_code": 3,
                "description": "Overcast",
                "high_c": 17.0,
                "low_c": 11.0,
            },
        ],
    }


def test_city_suggestions_returns_matching_locations(monkeypatch) -> None:
    async def fake_search_locations(city: str) -> list[main.Location]:
        assert city == "Lon"
        return [
            main.Location(
                name="London",
                country="United Kingdom",
                latitude=51.5,
                longitude=-0.12,
            )
        ]

    monkeypatch.setattr(main, "search_locations", fake_search_locations)

    response = client.get("/api/cities", params={"name": "Lon"})

    assert response.status_code == 200
    assert response.json()[0]["name"] == "London"
    assert response.json()[0]["country"] == "United Kingdom"


def test_city_suggestions_require_two_characters() -> None:
    response = client.get("/api/cities", params={"name": "L"})

    assert response.status_code == 422


def test_weather_endpoint_accepts_coordinates(monkeypatch) -> None:
    async def fake_fetch_weather_for_coordinates(
        latitude: float, longitude: float
    ) -> main.WeatherResponse:
        assert latitude == 18.52
        assert longitude == 73.86
        return sample_weather("Your location")

    monkeypatch.setattr(
        main,
        "fetch_weather_for_coordinates",
        fake_fetch_weather_for_coordinates,
    )

    response = client.get(
        "/api/weather",
        params={"latitude": 18.52, "longitude": 73.86},
    )

    assert response.status_code == 200
    assert response.json()["city"] == "Your location"


def test_weather_endpoint_requires_both_coordinates() -> None:
    response = client.get("/api/weather", params={"latitude": 18.52})

    assert response.status_code == 422


def test_weather_fetch_keeps_five_day_forecast_and_maps_ten_day_trend(
    monkeypatch,
) -> None:
    requested_params = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {
                "timezone": "Europe/London",
                "current": {
                    "temperature_2m": 18.5,
                    "apparent_temperature": 18.0,
                    "relative_humidity_2m": 62,
                    "wind_speed_10m": 12.0,
                    "weather_code": 2,
                    "is_day": 1,
                },
                "daily": {
                    "time": [
                        "2026-11-15",
                        "2026-11-16",
                        "2026-11-17",
                        "2026-11-18",
                        "2026-11-19",
                        "2026-11-20",
                        "2026-11-21",
                        "2026-11-22",
                        "2026-11-23",
                        "2026-11-24",
                    ],
                    "weather_code": [2, 3, 61, 0, 71, 2, 45, 80, 1, 95],
                    "temperature_2m_max": [19, 17, 15, 18, 8, 20, 13, 14, 21, 16],
                    "temperature_2m_min": [12, 11, 10, 9, 3, 13, 8, 9, 11, 12],
                },
            }

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            assert timeout == 10.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def get(self, url: str, params: dict) -> FakeResponse:
            assert url == main.FORECAST_URL
            requested_params.update(params)
            return FakeResponse()

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    weather = asyncio.run(
        main.fetch_weather_for_location(
            main.Location(
                name="London",
                country="United Kingdom",
                latitude=51.5,
                longitude=-0.12,
            )
        )
    )

    assert requested_params["forecast_days"] == 10
    assert len(weather.forecast) == 5
    assert len(weather.trend) == 10
    assert weather.forecast[0].description == "Partly cloudy"
    assert weather.forecast[0].high_c == 19
    assert weather.trend[9].description == "Thunderstorm"


def test_weather_endpoint_rejects_empty_city() -> None:
    response = client.get("/api/weather", params={"city": " "})

    assert response.status_code == 422
