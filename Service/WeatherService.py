from datetime import datetime

import httpx

from Service.TimezoneService import TimezoneService


class WeatherService:
    SUNNY_WEATHER_CODES = {0, 1}

    def __init__(self, timezone_service: TimezoneService | None = None):
        self.timezone_service = timezone_service or TimezoneService()

    def get_weather_snapshot(self, latitude, longitude, continente=None):
        if latitude is None or longitude is None:
            return {
                "weather_code": None,
                "is_sunny": False,
                "solar_active": False,
                "reason": "Localização indisponível",
                "checked_at": datetime.utcnow().isoformat(),
            }

        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "weather_code",
                "timezone": "auto",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current", {})
        weather_code = current.get("weather_code")

        local_now = datetime.now(
            self.timezone_service.get_timezone(latitude, longitude, continente)
        )
        is_sunny = weather_code in self.SUNNY_WEATHER_CODES
        daylight_window = 6 <= local_now.hour < 18
        solar_active = bool(is_sunny and daylight_window)

        if not is_sunny:
            reason = f"Clima não ensolarado (código {weather_code})"
        elif not daylight_window:
            reason = "Fora da janela solar local (06:00-18:00)"
        else:
            reason = "Energia solar disponível"

        return {
            "weather_code": weather_code,
            "is_sunny": is_sunny,
            "solar_active": solar_active,
            "reason": reason,
            "checked_at": local_now.isoformat(),
            "timezone": payload.get("timezone"),
        }