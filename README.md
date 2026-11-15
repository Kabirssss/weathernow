# Your first weather API

This project is a small weather app built with Python and FastAPI. It accepts a
city name, looks up the city's coordinates, gets current conditions, a 5-day
forecast, and a 10-day temperature trend from
[Open-Meteo](https://open-meteo.com/), and returns JSON.
The web page also offers city suggestions, recent searches, a Celsius/Fahrenheit
toggle, and optional current-location search. Open-Meteo does not require an
API key for this example.

## 1. Set up the project

Open a terminal in this folder and create a virtual environment. This keeps
the project's Python packages separate from other projects on your computer.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, activate it with `.venv\Scripts\activate` instead.
In VS Code, choose **Python: Select Interpreter** and select this project's
`.venv` environment if it is not selected automatically.

Install the project's dependencies:

```bash
python -m pip install -r requirements.txt
```

## 2. Run the API

```bash
uvicorn main:app --reload
```

Uvicorn starts a local development server. Keep that terminal open, then visit
<http://127.0.0.1:8000/> to use the weather search page. You can also visit
<http://127.0.0.1:8000/docs> to try the API directly in FastAPI's interactive
docs.

The page's HTML, CSS, and JavaScript live in the `static/` folder. The browser
asks `/api/cities` for suggestions as you type, then requests `/api/weather`
when you search. The same weather endpoint accepts latitude and longitude for
the current-location button. Recent searches and the chosen temperature unit
are saved in your browser.

The current-location feature requires your permission. Browsers allow location
access on `localhost` during development and on secure HTTPS websites after
deployment.

## 3. Try a weather request

In another terminal, or in your browser, request:

```text
http://127.0.0.1:8000/api/weather?city=London
```

The response is JSON, for example:

```json
{
  "city": "London",
  "country": "United Kingdom",
  "timezone": "Europe/London",
  "temperature_c": 18.5,
  "feels_like_c": 18.0,
  "humidity_percent": 62,
  "wind_speed_kmh": 12.0,
  "weather_code": 2,
  "description": "Partly cloudy",
  "is_day": true,
  "forecast": [
    {
      "date": "2026-11-15",
      "weather_code": 2,
      "description": "Partly cloudy",
      "high_c": 19.0,
      "low_c": 12.0
    }
  ]
}
```

Weather values change; the example above is only to show the response shape.
The `forecast` list retains five daily summaries for API clients. The page
shows the ten daily high/low values from `trend` as a chart instead of a
separate five-day panel. Hover over or keyboard-focus a date to see its
conditions and high/low temperatures; the first date is marked **Today**.
The Celsius/Fahrenheit toggle updates the chart and its detail popovers.

## How the request works

1. `GET /api/weather?city=London` is the route: it describes the HTTP method
   and URL used by a client.
2. FastAPI checks the `city` query parameter. A missing, empty, or overly long
   name is rejected with a `422` response.
3. `fetch_weather` asks Open-Meteo's geocoding service to turn the city into
   latitude and longitude.
4. It uses those coordinates to request current conditions and ten days of
   daily high/low temperatures from Open-Meteo.
5. The API keeps five days in `forecast` for clients and returns all ten days
   in `trend` for the chart shown by the page.
6. The `WeatherResponse` model defines the JSON fields this API returns.
7. The browser shows the result, converts temperatures when you change units,
   and remembers city searches in local storage.

If the city cannot be found, the API responds with `404`. If the weather
provider is unavailable or sends an unexpected response, the API responds with
`502`.

## Run the tests

With the virtual environment activated:

```bash
pytest
```

The tests check the API's response and input validation without relying on a
live weather service.
