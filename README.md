# Your first weather API
Try out the App for free: https://weathernow-xedk.vercel.app/

This project is a small weather app built with Python and FastAPI. It accepts a
city name, looks up the city's coordinates, gets current conditions, a 5-day
forecast, and a 10-day temperature trend from
[Open-Meteo](https://open-meteo.com/), and returns JSON.
The web page also offers city suggestions, recent searches, a Celsius/Fahrenheit
toggle, and optional current-location search. Open-Meteo does not require an
API key for weather. The optional Gemini-powered weather chat uses a private
server-side API key.

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

## Configure the Gemini weather assistant

Create a Gemini API key in Google AI Studio. Do not paste the key into browser
JavaScript, commit it, or send it in chat. Copy the example environment file
and add your key to the local `.env` file:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder value for `GEMINI_API_KEY`. The `.env`
file is ignored by Git. `GEMINI_MODEL` defaults to `gemini-3.8-flash`; change
it in `.env` if you want to use another model available to your account.
Restart the server after changing environment values. If an older `.env` still
sets `GEMINI_MODEL=gemini-2.5-flash`, update that line to
`GEMINI_MODEL=gemini-3.8-flash`.

To test the Gemini key and model directly, independently of the weather chat
route, run:

```bash
./.venv/bin/python check_gemini.py
```

This makes one small Gemini request and prints the configured model and
response, or Gemini's HTTP status and error message. It never prints the API
key. If this succeeds but chat still fails, the issue is in the app request;
if this fails with 503 too, Gemini is rejecting the request before the app's
weather-chat prompt is involved. Gemini can temporarily return 503 during
high demand; wait a few minutes and run the test again.

## 2. Run the API

```bash
./.venv/bin/python -m uvicorn main:app --reload
```

Uvicorn starts a local development server. Keep that terminal open, then visit
<http://127.0.0.1:8000/> to use the weather search page. You can also visit
<http://127.0.0.1:8000/docs> to try the API directly in FastAPI's interactive
docs.

Using `./.venv/bin/python -m uvicorn` ensures the server uses the same
environment where `google-genai` was installed. If you see
`ImportError: cannot import name 'genai' from 'google'`, stop the server and
run it with this command from the project folder. If dependencies are not
installed in `.venv`, run:

```bash
./.venv/bin/python -m pip install -r requirements.txt
```

The page's HTML, CSS, and JavaScript live in the `static/` folder. The browser
asks `/api/cities` for suggestions as you type, then requests `/api/weather`
when you search. The same weather endpoint accepts latitude and longitude for
the current-location button. The Gemini chat sends requests to your FastAPI
server at `/api/chat`; the server adds current weather context and calls Gemini
without exposing the key to the browser. Recent searches and the chosen
temperature unit are saved in your browser.

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
`502`. The chat endpoint responds with `503` if `GEMINI_API_KEY` is not set,
and with `502` if Gemini is unavailable.

## Run the tests

With the virtual environment activated:

```bash
pytest
```

The tests check the API's response and input validation without relying on a
live weather service.
