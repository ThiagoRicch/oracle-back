from zoneinfo import ZoneInfo


class TimezoneService:
    CONTINENT_DEFAULTS = {
        "America do Sul": "America/Sao_Paulo",
        "America do Norte": "America/New_York",
        "America Central": "America/Panama",
        "Europa": "Europe/Berlin",
        "Asia": "Asia/Tokyo",
        "Africa": "Africa/Johannesburg",
        "Oceania": "Australia/Sydney",
    }

    COUNTRY_TIMEZONES = {
        "Brasil": "America/Sao_Paulo",
        "Argentina": "America/Argentina/Buenos_Aires",
        "Colômbia": "America/Bogota",
        "Peru": "America/Lima",
        "Chile": "America/Santiago",
        "Estados Unidos": "America/New_York",
        "Canadá": "America/Toronto",
        "México": "America/Mexico_City",
        "Costa Rica": "America/Costa_Rica",
        "Panamá": "America/Panama",
        "Alemanha": "Europe/Berlin",
        "França": "Europe/Paris",
        "Reino Unido": "Europe/London",
        "Itália": "Europe/Rome",
        "Espanha": "Europe/Madrid",
        "Portugal": "Europe/Lisbon",
        "China": "Asia/Shanghai",
        "Índia": "Asia/Kolkata",
        "Japão": "Asia/Tokyo",
        "Nigéria": "Africa/Lagos",
        "Egito": "Africa/Cairo",
        "África do Sul": "Africa/Johannesburg",
        "Austrália": "Australia/Sydney",
        "Nova Zelândia": "Pacific/Auckland",
    }

    CITY_TIMEZONES = {
        "São Paulo": "America/Sao_Paulo",
        "Rio de Janeiro": "America/Sao_Paulo",
        "Buenos Aires": "America/Argentina/Buenos_Aires",
        "Córdoba": "America/Argentina/Cordoba",
        "Bogotá": "America/Bogota",
        "Medellín": "America/Bogota",
        "Lima": "America/Lima",
        "Arequipa": "America/Lima",
        "Santiago": "America/Santiago",
        "Valparaíso": "America/Santiago",
        "Nova York": "America/New_York",
        "Los Angeles": "America/Los_Angeles",
        "Toronto": "America/Toronto",
        "Vancouver": "America/Vancouver",
        "Cidade do México": "America/Mexico_City",
        "Guadalajara": "America/Mexico_City",
        "San José": "America/Costa_Rica",
        "Limón": "America/Costa_Rica",
        "Cidade do Panamá": "America/Panama",
        "Colón": "America/Panama",
        "Berlim": "Europe/Berlin",
        "Munique": "Europe/Berlin",
        "Paris": "Europe/Paris",
        "Lyon": "Europe/Paris",
        "Londres": "Europe/London",
        "Manchester": "Europe/London",
        "Roma": "Europe/Rome",
        "Milão": "Europe/Rome",
        "Madri": "Europe/Madrid",
        "Barcelona": "Europe/Madrid",
        "Lisboa": "Europe/Lisbon",
        "Porto": "Europe/Lisbon",
        "Pequim": "Asia/Shanghai",
        "Xangai": "Asia/Shanghai",
        "Nova Délhi": "Asia/Kolkata",
        "Mumbai": "Asia/Kolkata",
        "Tóquio": "Asia/Tokyo",
        "Osaka": "Asia/Tokyo",
        "Abuja": "Africa/Lagos",
        "Lagos": "Africa/Lagos",
        "Cairo": "Africa/Cairo",
        "Alexandria": "Africa/Cairo",
        "Pretória": "Africa/Johannesburg",
        "Cidade do Cabo": "Africa/Johannesburg",
        "Sydney": "Australia/Sydney",
        "Melbourne": "Australia/Melbourne",
        "Auckland": "Pacific/Auckland",
        "Wellington": "Pacific/Auckland",
    }

    def resolve_timezone_name(self, latitude, longitude, continente=None, pais=None, cidade=None):
        if cidade and cidade in self.CITY_TIMEZONES:
            return self.CITY_TIMEZONES[cidade]

        if pais and pais in self.COUNTRY_TIMEZONES:
            return self.COUNTRY_TIMEZONES[pais]

        if continente:
            return self.CONTINENT_DEFAULTS.get(continente, "UTC")

        return "UTC"

    def get_timezone(self, latitude, longitude, continente=None, pais=None, cidade=None):
        timezone_name = self.resolve_timezone_name(latitude, longitude, continente, pais, cidade)
        return ZoneInfo(timezone_name)
