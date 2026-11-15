const form = document.querySelector("#search-form");
const cityInput = document.querySelector("#city-input");
const suggestions = document.querySelector("#city-suggestions");
const searchButton = document.querySelector("#search-button");
const locationButton = document.querySelector("#location-button");
const unitToggle = document.querySelector("#unit-toggle");
const statusMessage = document.querySelector("#status-message");
const weatherCard = document.querySelector("#weather-card");
const recentSection = document.querySelector("#recent-section");
const recentSearches = document.querySelector("#recent-searches");
const trendChart = document.querySelector("#trend-chart");
const chatLauncher = document.querySelector("#chat-launcher");
const chatPanel = document.querySelector("#chat-panel");
const chatClose = document.querySelector("#chat-close");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const chatSend = document.querySelector("#chat-send");
const chatMessages = document.querySelector("#chat-messages");

const RECENT_SEARCHES_KEY = "weather-now.recent-searches";
const TEMPERATURE_UNIT_KEY = "weather-now.temperature-unit";
const MAX_RECENT_SEARCHES = 5;

let currentWeather = null;
let unit = readStoredUnit();
let suggestionsTimer;
let suggestionsController;
let tooltipHideTimer;
let chatHistory = [];

function setStatus(message, state = "info") {
  statusMessage.textContent = message;
  statusMessage.dataset.state = state;
}

function readStoredUnit() {
  try {
    return localStorage.getItem(TEMPERATURE_UNIT_KEY) === "F" ? "F" : "C";
  } catch (error) {
    console.warn("Could not read the saved temperature unit.", error);
    return "C";
  }
}

function readRecentSearches() {
  try {
    const saved = JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) || "[]");
    return Array.isArray(saved)
      ? saved.filter((city) => typeof city === "string").slice(0, MAX_RECENT_SEARCHES)
      : [];
  } catch (error) {
    console.warn("Could not read recent city searches.", error);
    return [];
  }
}

function saveRecentSearch(city) {
  try {
    const updated = [
      city,
      ...readRecentSearches().filter(
        (recentCity) => recentCity.toLowerCase() !== city.toLowerCase(),
      ),
    ].slice(0, MAX_RECENT_SEARCHES);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
    renderRecentSearches(updated);
    return true;
  } catch (error) {
    console.warn("Could not save this city to recent searches.", error);
    return false;
  }
}

function renderRecentSearches(cities = readRecentSearches()) {
  recentSearches.replaceChildren();
  recentSection.hidden = cities.length === 0;

  for (const city of cities) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "recent-chip";
    button.textContent = city;
    button.addEventListener("click", () => {
      cityInput.value = city;
      loadWeather(new URLSearchParams({ city }), city);
    });
    recentSearches.append(button);
  }
}

function formatTemperature(celsius) {
  return `${Math.round(toDisplayTemperature(celsius))}°${unit}`;
}

function toDisplayTemperature(celsius) {
  return unit === "C" ? celsius : (celsius * 9) / 5 + 32;
}

function describeWeatherIcon(code, isDay) {
  if (code === 0) {
    return { icon: isDay ? "☀️" : "🌙", theme: isDay ? "clear" : "night" };
  }
  if (code === 1 || code === 2) {
    return { icon: isDay ? "🌤️" : "☁️", theme: "partly-cloudy" };
  }
  if (code === 3 || code === 45 || code === 48) {
    return { icon: "☁️", theme: "cloudy" };
  }
  if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) {
    return { icon: "🌧️", theme: "rain" };
  }
  if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) {
    return { icon: "❄️", theme: "snow" };
  }
  if (code >= 95) {
    return { icon: "⛈️", theme: "storm" };
  }
  return { icon: "🌤️", theme: "partly-cloudy" };
}

function formatForecastDate(date, options) {
  return new Date(`${date}T12:00:00`).toLocaleDateString(undefined, options);
}

function showTrendTooltip(day, marker) {
  clearTimeout(tooltipHideTimer);
  let tooltip = trendChart.querySelector(".trend-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = "trend-tooltip";
    tooltip.id = "trend-tooltip";
    tooltip.setAttribute("role", "tooltip");
    trendChart.append(tooltip);
  }

  const date = document.createElement("p");
  date.className = "tooltip-date";
  date.textContent = formatForecastDate(day.date, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const conditions = document.createElement("p");
  conditions.className = "tooltip-conditions";
  const icon = describeWeatherIcon(day.weather_code, true).icon;
  conditions.textContent = `${icon} ${day.description}`;

  const temperatures = document.createElement("p");
  temperatures.className = "tooltip-temperatures";
  temperatures.textContent =
    `High ${formatTemperature(day.high_c)} · Low ${formatTemperature(day.low_c)}`;

  tooltip.replaceChildren(date, conditions, temperatures);
  tooltip.hidden = false;

  const markerCenter = marker.offsetLeft + marker.offsetWidth / 2;
  const edgePadding = tooltip.offsetWidth / 2 + 10;
  const center = Math.min(
    Math.max(markerCenter, edgePadding),
    trendChart.scrollWidth - edgePadding,
  );
  tooltip.style.left = `${center}px`;
}

function scheduleTrendTooltipHide() {
  tooltipHideTimer = setTimeout(() => {
    const tooltip = trendChart.querySelector(".trend-tooltip");
    if (tooltip) {
      tooltip.hidden = true;
    }
  }, 140);
}

function renderTemperatureTrend(days) {
  trendChart.replaceChildren();
  if (!days.length) {
    return;
  }

  const width = 760;
  const height = 270;
  const left = 48;
  const right = 18;
  const top = 20;
  const bottom = 18;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const temperatures = days.flatMap((day) => [
    toDisplayTemperature(day.high_c),
    toDisplayTemperature(day.low_c),
  ]);
  const minTemperature = Math.floor(Math.min(...temperatures) / 5) * 5;
  const maxTemperature = Math.ceil(Math.max(...temperatures) / 5) * 5;
  const temperatureRange = Math.max(maxTemperature - minTemperature, 5);
  const x = (index) => left + (plotWidth * index) / Math.max(days.length - 1, 1);
  const y = (temperature) =>
    top + (plotHeight * (maxTemperature - temperature)) / temperatureRange;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-labelledby", "trend-chart-title trend-chart-description");

  const title = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "title",
  );
  title.setAttribute("id", "trend-chart-title");
  title.textContent = "Ten-day high and low temperature trend";
  svg.append(title);

  const description = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "desc",
  );
  description.setAttribute("id", "trend-chart-description");
  description.textContent =
    `Daily high and low temperatures for the next ${days.length} days, in degrees ${unit === "C" ? "Celsius" : "Fahrenheit"}.`;
  svg.append(description);

  const grid = document.createElementNS("http://www.w3.org/2000/svg", "g");
  grid.setAttribute("class", "chart-grid");
  for (let index = 0; index <= 4; index += 1) {
    const temperature = maxTemperature - (temperatureRange * index) / 4;
    const yPosition = top + (plotHeight * index) / 4;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", String(left));
    line.setAttribute("x2", String(width - right));
    line.setAttribute("y1", String(yPosition));
    line.setAttribute("y2", String(yPosition));
    grid.append(line);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(left - 10));
    label.setAttribute("y", String(yPosition + 4));
    label.setAttribute("text-anchor", "end");
    label.textContent = `${formatTemperature(temperature)}`;
    grid.append(label);
  }
  svg.append(grid);

  for (const [seriesName, valueKey, className] of [
    ["High", "high_c", "high"],
    ["Low", "low_c", "low"],
  ]) {
    const series = document.createElementNS("http://www.w3.org/2000/svg", "g");
    series.setAttribute("class", `chart-series ${className}`);

    const line = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "polyline",
    );
    line.setAttribute(
      "points",
      days
        .map((day, index) => {
          return `${x(index)},${y(toDisplayTemperature(day[valueKey]))}`;
        })
        .join(" "),
    );
    series.append(line);

    for (const [index, day] of days.entries()) {
      const value = toDisplayTemperature(day[valueKey]);
      const point = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "circle",
      );
      point.setAttribute("cx", String(x(index)));
      point.setAttribute("cy", String(y(value)));
      point.setAttribute("r", "4");

      const pointTitle = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "title",
      );
      pointTitle.textContent =
        `${seriesName}: ${formatTemperature(day[valueKey])} on ${day.date}`;
      point.append(pointTitle);
      series.append(point);
    }

    svg.append(series);
  }

  for (const [index, day] of days.entries()) {
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = `trend-date-marker${index === 0 ? " is-today" : ""}`;
    marker.setAttribute("aria-describedby", "trend-tooltip");
    marker.setAttribute(
      "aria-label",
      `${index === 0 ? "Today, " : ""}${formatForecastDate(day.date, {
        weekday: "long",
        month: "long",
        day: "numeric",
      })}. ${day.description}. High ${formatTemperature(day.high_c)}, low ${formatTemperature(day.low_c)}.`,
    );

    const weekday = document.createElement("span");
    weekday.className = "trend-date-weekday";
    weekday.textContent =
      index === 0 ? "TODAY" : formatForecastDate(day.date, { weekday: "short" });

    const date = document.createElement("span");
    date.className = "trend-date-value";
    date.textContent = formatForecastDate(day.date, {
      month: "short",
      day: "numeric",
    });

    marker.append(weekday, date);
    marker.addEventListener("pointerenter", () => showTrendTooltip(day, marker));
    marker.addEventListener("pointerleave", scheduleTrendTooltipHide);
    marker.addEventListener("focus", () => showTrendTooltip(day, marker));
    marker.addEventListener("blur", scheduleTrendTooltipHide);
    trendChart.append(marker);
  }
  trendChart.prepend(svg);

  const tooltip = document.createElement("div");
  tooltip.className = "trend-tooltip";
  tooltip.id = "trend-tooltip";
  tooltip.setAttribute("role", "tooltip");
  tooltip.hidden = true;
  tooltip.addEventListener("pointerenter", () => clearTimeout(tooltipHideTimer));
  tooltip.addEventListener("pointerleave", scheduleTrendTooltipHide);
  trendChart.append(tooltip);
}

function displayWeather(weather) {
  if (
    currentWeather &&
    (currentWeather.city !== weather.city ||
      currentWeather.country !== weather.country)
  ) {
    resetChatConversation();
  }
  currentWeather = weather;
  const place = weather.country
    ? `${weather.city}, ${weather.country}`
    : weather.city;

  document.querySelector("#location-name").textContent = place;
  document.querySelector("#location-timezone").textContent = weather.timezone;
  document.querySelector("#temperature").textContent =
    formatTemperature(weather.temperature_c);
  document.querySelector("#weather-description").textContent =
    weather.description;
  document.querySelector("#feels-like").textContent =
    `Feels like ${formatTemperature(weather.feels_like_c)}`;
  document.querySelector("#humidity").textContent =
    `${weather.humidity_percent}%`;
  document.querySelector("#wind").textContent =
    `${weather.wind_speed_kmh} km/h`;
  document.querySelector("#daylight").textContent =
    weather.is_day ? "Daytime" : "Nighttime";

  const presentation = describeWeatherIcon(weather.weather_code, weather.is_day);
  document.querySelector("#weather-symbol").textContent = presentation.icon;
  document.body.dataset.weather = presentation.theme;
  unitToggle.textContent = `°${unit}`;
  unitToggle.setAttribute(
    "aria-label",
    `Switch to ${unit === "C" ? "Fahrenheit" : "Celsius"}`,
  );
  renderTemperatureTrend(weather.trend);
  weatherCard.hidden = false;
}

function resetChatConversation() {
  chatHistory = [];
  chatMessages.replaceChildren();
  appendChatMessage(
    "assistant",
    "Weather updated. Ask me about these conditions or the forecast.",
  );
}

function appendChatMessage(role, text) {
  const message = document.createElement("p");
  message.className = `chat-message ${role}`;
  message.textContent = text;
  chatMessages.append(message);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setChatOpen(open) {
  chatPanel.hidden = !open;
  chatLauncher.setAttribute("aria-expanded", String(open));
  if (open) {
    chatInput.focus();
  }
}

async function sendChatMessage(message) {
  chatSend.disabled = true;
  chatInput.disabled = true;
  appendChatMessage("user", message);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: chatHistory.slice(-12),
        weather: currentWeather,
      }),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "The weather assistant could not reply.");
    }

    chatHistory.push(
      { role: "user", text: message },
      { role: "model", text: result.reply },
    );
    chatHistory = chatHistory.slice(-12);
    appendChatMessage("assistant", result.reply);
  } catch (error) {
    appendChatMessage(
      "assistant error",
      error instanceof Error
        ? error.message
        : "Something went wrong. Please try again.",
    );
  } finally {
    chatSend.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
}

async function loadWeather(query, description) {
  searchButton.disabled = true;
  locationButton.disabled = true;
  setStatus(`Looking up the weather for ${description}…`);

  try {
    const response = await fetch(`/api/weather?${query}`);
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "Could not retrieve the weather.");
    }

    displayWeather(result);
    const saved = result.city === "Your location" || saveRecentSearch(description);
    setStatus(
      saved
        ? `Showing current weather for ${result.city}.`
        : `Showing current weather for ${result.city}. Recent searches could not be saved in this browser.`,
      saved ? "info" : "error",
    );
  } catch (error) {
    weatherCard.hidden = true;
    delete document.body.dataset.weather;
    setStatus(
      error instanceof Error
        ? error.message
        : "Something went wrong. Please try again.",
      "error",
    );
  } finally {
    searchButton.disabled = false;
    locationButton.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const city = cityInput.value.trim();
  if (!city) {
    setStatus("Please enter a city name.", "error");
    cityInput.focus();
    return;
  }

  loadWeather(new URLSearchParams({ city }), city);
});

cityInput.addEventListener("input", () => {
  clearTimeout(suggestionsTimer);
  suggestionsController?.abort();

  const name = cityInput.value.trim();
  if (name.length < 2) {
    suggestions.replaceChildren();
    return;
  }

  suggestionsTimer = setTimeout(async () => {
    suggestionsController = new AbortController();
    try {
      const query = new URLSearchParams({ name });
      const response = await fetch(`/api/cities?${query}`, {
        signal: suggestionsController.signal,
      });
      const cities = await response.json();
      if (!response.ok) {
        throw new Error(cities.detail || "City suggestions are unavailable.");
      }

      suggestions.replaceChildren();
      for (const city of cities) {
        const option = document.createElement("option");
        option.value = city.country ? `${city.name}, ${city.country}` : city.name;
        suggestions.append(option);
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      console.warn("Could not load city suggestions.", error);
    }
  }, 250);
});

locationButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setStatus("Your browser does not support location access.", "error");
    return;
  }

  searchButton.disabled = true;
  locationButton.disabled = true;
  setStatus("Finding your location…");

  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      const query = new URLSearchParams({
        latitude: String(coords.latitude),
        longitude: String(coords.longitude),
      });
      loadWeather(query, "your location");
    },
    (error) => {
      const messages = {
        1: "Location permission was denied. Allow location access or search for a city.",
        2: "Your location could not be determined. Try searching for a city instead.",
        3: "Location lookup timed out. Please try again.",
      };
      setStatus(messages[error.code] || "Could not access your location.", "error");
      searchButton.disabled = false;
      locationButton.disabled = false;
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
  );
});

unitToggle.addEventListener("click", () => {
  unit = unit === "C" ? "F" : "C";
  try {
    localStorage.setItem(TEMPERATURE_UNIT_KEY, unit);
  } catch (error) {
    console.warn("Could not save the temperature unit preference.", error);
  }
  if (currentWeather) {
    displayWeather(currentWeather);
  }
});

renderRecentSearches();
unitToggle.textContent = `°${unit}`;
unitToggle.setAttribute(
  "aria-label",
  `Switch to ${unit === "C" ? "Fahrenheit" : "Celsius"}`,
);

chatLauncher.addEventListener("click", () => {
  setChatOpen(chatPanel.hidden);
});

chatClose.addEventListener("click", () => {
  setChatOpen(false);
  chatLauncher.focus();
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) {
    return;
  }
  chatInput.value = "";
  sendChatMessage(message);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !chatPanel.hidden) {
    setChatOpen(false);
    chatLauncher.focus();
  }
});
