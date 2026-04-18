import hashlib
import math
import random
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class CurrencyProfile:
    code: str
    symbol: str
    tariff_per_kwh: float
    usd_exchange_rate: float


COUNTRY_PRICING = {
    "Brasil": CurrencyProfile("BRL", "R$", 0.82, 5.10),
    "Argentina": CurrencyProfile("ARS", "$", 110.0, 980.0),
    "Colômbia": CurrencyProfile("COP", "$", 720.0, 3950.0),
    "Peru": CurrencyProfile("PEN", "S/", 0.78, 3.75),
    "Chile": CurrencyProfile("CLP", "$", 165.0, 960.0),
    "Estados Unidos": CurrencyProfile("USD", "$", 0.18, 1.0),
    "Canadá": CurrencyProfile("CAD", "C$", 0.19, 1.37),
    "México": CurrencyProfile("MXN", "$", 3.6, 16.8),
    "Costa Rica": CurrencyProfile("CRC", "₡", 78.0, 510.0),
    "Panamá": CurrencyProfile("PAB", "B/.", 0.17, 1.0),
    "Alemanha": CurrencyProfile("EUR", "€", 0.33, 0.92),
    "França": CurrencyProfile("EUR", "€", 0.28, 0.92),
    "Reino Unido": CurrencyProfile("GBP", "£", 0.24, 0.79),
    "Itália": CurrencyProfile("EUR", "€", 0.30, 0.92),
    "Espanha": CurrencyProfile("EUR", "€", 0.27, 0.92),
    "Portugal": CurrencyProfile("EUR", "€", 0.24, 0.92),
    "China": CurrencyProfile("CNY", "¥", 0.62, 7.24),
    "Índia": CurrencyProfile("INR", "₹", 8.1, 83.2),
    "Japão": CurrencyProfile("JPY", "¥", 31.0, 154.0),
    "Nigéria": CurrencyProfile("NGN", "₦", 240.0, 1450.0),
    "Egito": CurrencyProfile("EGP", "E£", 8.2, 49.0),
    "África do Sul": CurrencyProfile("ZAR", "R", 3.4, 18.3),
    "Austrália": CurrencyProfile("AUD", "A$", 0.29, 1.56),
    "Nova Zelândia": CurrencyProfile("NZD", "NZ$", 0.31, 1.68),
}

DEFAULT_PROFILE = CurrencyProfile("USD", "$", 0.18, 1.0)


class EnergyMonitoringService:
    def _daily_consumption_kwh(self, servidor_id: str, current_date: date) -> float:
        # Simulacao de consumo diario com variacao por dia e servidor.
        seed = f"{servidor_id}:{current_date.isoformat()}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        seed_value = int(digest[:16], 16)
        rng = random.Random(seed_value)
        return float(rng.randint(80, 180))

    def _monthly_consumption_samples(self, servidor_id: str, reference_date: date):
        _, days_in_month = monthrange(reference_date.year, reference_date.month)
        first_day = reference_date.replace(day=1)
        for offset in range(days_in_month):
            current = first_day + timedelta(days=offset)
            yield self._daily_consumption_kwh(servidor_id, current)

    def build_daily_metrics(self, servidor: dict, reference_date: date | None = None):
        current_date = reference_date or datetime.utcnow().date()
        consumption_kwh = self._daily_consumption_kwh(str(servidor.get("id")), current_date)
        power_watts = math.floor((consumption_kwh * 1000) / 24)
        return self._build_costs(servidor, consumption_kwh, power_watts, current_date)

    def build_monthly_metrics(self, servidor: dict, reference_date: date | None = None):
        current_date = reference_date or datetime.utcnow().date()
        samples = list(self._monthly_consumption_samples(str(servidor.get("id")), current_date))
        consumption_kwh = round(sum(samples), 2)
        avg_daily_kwh = (consumption_kwh / len(samples)) if samples else 0
        avg_power_watts = math.floor((avg_daily_kwh * 1000) / 24) if samples else 0
        return self._build_costs(servidor, consumption_kwh, avg_power_watts, current_date)

    def _build_costs(self, servidor: dict, consumption_kwh: float, power_watts: int, reference_date: date):
        profile = COUNTRY_PRICING.get(servidor.get("pais"), DEFAULT_PROFILE)
        local_cost = round(consumption_kwh * profile.tariff_per_kwh, 2)
        usd_cost = round(local_cost / profile.usd_exchange_rate, 2) if profile.usd_exchange_rate else local_cost
        return {
            "reference_date": reference_date.isoformat(),
            "power_watts": power_watts,
            "consumption_kwh": consumption_kwh,
            "currency_code": profile.code,
            "currency_symbol": profile.symbol,
            "local_cost": local_cost,
            "usd_cost": usd_cost,
        }