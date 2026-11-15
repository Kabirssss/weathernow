const form = document.querySelector("#search-form");
const cityInput = document.querySelector("#city-input");
const searchButton = document.querySelector("#search-button");
const statusMessage = document.querySelector("#status-message");
const weatherCard = document.querySelector("#weather-card");

function setStatus(message, state = "info") {
  statusMessage.textContent = message;
  statusMessage.dataset.state = state;
}

function displayWeather(weather) {
  const place = weather.country
    ? `${weather.city}, ${weather.country}`
    : weather.city;

  document.querySelector("#location-name").textContent = place;
  document.querySelector("#location-timezone").textContent = weather.timezone;
  document.querySelector("#temperature").textContent =
    `${weather.temperature_c}°`;
  document.querySelector("#weather-description").textContent =
    weather.description;
  document.querySelector("#feels-like").textContent =
    `Feels like ${weather.feels_like_c}°C`;
  document.querySelector("#humidity").textContent =
    `${weather.humidity_percent}%`;
  document.querySelector("#wind").textContent =
    `${weather.wind_speed_kmh} km/h`;
  document.querySelector("#daylight").textContent =
    weather.is_day ? "Daytime" : "Nighttime";

  weatherCard.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const city = cityInput.value.trim();
  if (!city) {
    setStatus("Please enter a city name.", "error");
    cityInput.focus();
    return;
  }

  searchButton.disabled = true;
  setStatus(`Looking up the weather for ${city}…`);

  try {
    const query = new URLSearchParams({ city });
    const response = await fetch(`/api/weather?${query}`);
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "Could not retrieve the weather.");
    }

    displayWeather(result);
    setStatus(`Showing current weather for ${result.city}.`);
  } catch (error) {
    weatherCard.hidden = true;
    setStatus(
      error instanceof Error
        ? error.message
        : "Something went wrong. Please try again.",
      "error",
    );
  } finally {
    searchButton.disabled = false;
  }
});
