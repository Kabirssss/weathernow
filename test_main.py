from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_home_page_is_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Weather, wherever you are." in response.text


def test_frontend_assets_are_served() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "api/weather" in response.text


def test_weather_endpoint_returns_weather(monkeypatch) -> None:
    async def fake_fetch_weather(city: str) -> main.WeatherResponse:
        assert city == "London"
        return main.WeatherResponse(
            city="London",
            country="United Kingdom",
            timezone="Europe/London",
            temperature_c=18.5,
            feels_like_c=18.0,
            humidity_percent=62,
            wind_speed_kmh=12.0,
            weather_code=2,
            description="Partly cloudy",
            is_day=True,
        )

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
    }


def test_weather_endpoint_rejects_empty_city() -> None:
    response = client.get("/api/weather", params={"city": " "})

    assert response.status_code == 422
