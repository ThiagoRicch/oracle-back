from fastapi import APIRouter

from Enum.Pais import PAISES

router = APIRouter(prefix="/geografia", tags=["Geografia"])

COUNTRY_ISO2 = {
    "Brasil": "BR",
    "Argentina": "AR",
    "Colombia": "CO",
    "Peru": "PE",
    "Chile": "CL",
    "Estados Unidos": "US",
    "Canada": "CA",
    "Mexico": "MX",
    "Costa Rica": "CR",
    "Panama": "PA",
    "Alemanha": "DE",
    "Franca": "FR",
    "Reino Unido": "GB",
    "Italia": "IT",
    "Espanha": "ES",
    "Portugal": "PT",
    "China": "CN",
    "India": "IN",
    "Japao": "JP",
    "Nigeria": "NG",
    "Egito": "EG",
    "Africa do Sul": "ZA",
    "Australia": "AU",
    "Nova Zelandia": "NZ",
}


def normalize_country_name(name: str) -> str:
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    normalized = name.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized.title()


def iso2_to_flag(iso2: str) -> str:
    iso = iso2.upper()
    if len(iso) != 2:
        return ""
    return chr(ord(iso[0]) + 127397) + chr(ord(iso[1]) + 127397)


@router.get("/")
def listar_geografia():
    resultado = []

    for continente, paises in PAISES.items():
        paises_serializados = []

        for pais in paises:
            iso2 = COUNTRY_ISO2.get(pais.nome) or COUNTRY_ISO2.get(normalize_country_name(pais.nome), "")

            cidades = []
            for idx, localizacao in enumerate(pais.localizacoes):
                cidades.append(
                    {
                        "nome": localizacao["cidade"],
                        "lat": localizacao["latitude"],
                        "lng": localizacao["longitude"],
                        "indice": idx,
                    }
                )

            paises_serializados.append(
                {
                    "nome": pais.nome,
                    "iso2": iso2,
                    "flag": iso2_to_flag(iso2) if iso2 else "",
                    "cidades": cidades,
                }
            )

        resultado.append(
            {
                "nome": continente.value,
                "paises": paises_serializados,
            }
        )

    return resultado
