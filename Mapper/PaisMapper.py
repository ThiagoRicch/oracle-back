from Enum.Pais import PAISES


def _normalize(value: str) -> str:
    text = (value or '').lower().strip()
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
        'é': 'e', 'ê': 'e',
        'í': 'i',
        'ó': 'o', 'ô': 'o', 'õ': 'o',
        'ú': 'u',
        'ç': 'c',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    alias = {
        'nova': 'nova zelandia',
    }
    return alias.get(text, text)

def buscar_pais(nome_pais: str):
    normalized_target = _normalize(nome_pais)
    for continente, paises in PAISES.items():
        for pais in paises:
            if _normalize(pais.nome) == normalized_target:
                return pais
    return None

def get_latitude(nome_pais: str, indice : int = 0):
    pais = buscar_pais(nome_pais)
    return pais.localizacoes[indice]["latitude"] if pais and pais.localizacoes else None

def get_longitude(nome_pais: str, indice : int = 0):
    pais = buscar_pais(nome_pais)
    return pais.localizacoes[indice]["longitude"] if pais and pais.localizacoes else None

def get_cidade(nome_pais: str, indice : int = 0):
    pais = buscar_pais(nome_pais)
    return pais.localizacoes[indice]["cidade"] if pais and pais.localizacoes else None

def get_indice_cidade(nome_pais: str, nome_cidade: str):
    pais = buscar_pais(nome_pais)
    if not pais or not pais.localizacoes:
        return None

    normalized_target = _normalize(nome_cidade)
    for idx, localizacao in enumerate(pais.localizacoes):
        cidade = localizacao.get("cidade") if isinstance(localizacao, dict) else None
        if cidade and _normalize(cidade) == normalized_target:
            return idx

    return None

def get_continente(nome_pais: str):
    normalized_target = _normalize(nome_pais)
    for continente, paises in PAISES.items():
        for pais in paises:
            if _normalize(pais.nome) == normalized_target:
                return continente.value
    return None