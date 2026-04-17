from datetime import datetime, timezone
import os

from dotenv import load_dotenv
from supabase import create_client

from Entity.Servidor import Servidor
from Enum.Pais import PAISES
from Mapper.PaisMapper import get_cidade, get_continente, get_indice_cidade, get_latitude, get_longitude


load_dotenv()

supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not os.getenv("SUPABASE_URL") or not supabase_key:
    raise RuntimeError("Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no arquivo .env")

supabase = create_client(os.getenv("SUPABASE_URL"), supabase_key)


class ServidorRepository:
    @staticmethod
    def _normalize_country_name(pais: str) -> str:
        raw = (pais or "").strip()

        lowered = raw.lower()
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
        for source, target in replacements.items():
            lowered = lowered.replace(source, target)

        alias = {
            "nova": "Nova Zelândia",
            "nova zelandia": "Nova Zelândia",
            "franca": "França",
            "italia": "Itália",
            "japao": "Japão",
            "canada": "Canadá",
            "mexico": "México",
            "panama": "Panamá",
            "colombia": "Colômbia",
            "africa do sul": "África do Sul",
            "australia": "Austrália",
        }
        return alias.get(lowered, raw)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def criar_servidor(self, nome, pais, indice: int = 0, capacidade_atual: int = 0, status: bool = True):
        pais = self._normalize_country_name(pais)
        data = {
            "nome": nome,
            "capacidade_total": Servidor.CAPACIDADE_TOTAL,
            "capacidade_atual": capacidade_atual,
            "pais": pais,
            "latitude": get_latitude(pais, indice),
            "longitude": get_longitude(pais, indice),
            "continente": get_continente(pais),
            "cidade": get_cidade(pais, indice),
            "status": status,
            "create_at": self._now_iso(),
            "disabled_at": None,
            "reactivated_at": None,
        }
        try:
            response = supabase.table("servidores").insert(data).execute()
        except Exception:
            fallback_data = {
                "nome": nome,
                "capacidade_total": Servidor.CAPACIDADE_TOTAL,
                "capacidade_atual": capacidade_atual,
                "pais": pais,
                "latitude": get_latitude(pais, indice),
                "longitude": get_longitude(pais, indice),
                "continente": get_continente(pais),
                "cidade": get_cidade(pais, indice),
                "status": status,
            }
            response = supabase.table("servidores").insert(fallback_data).execute()
        return [self._decorate_server(record) for record in response.data]

    def _normalize_records_country(self, records):
        normalized = []
        for record in records or []:
            if isinstance(record, dict) and "pais" in record:
                record["pais"] = self._normalize_country_name(record["pais"])
            normalized.append(record)
        return normalized

    def listar_servidores(self):
        response = supabase.table("servidores").select("*").execute()
        return [self._decorate_server(record) for record in self._normalize_records_country(response.data)]

    def listar_servidor_por_id(self, servidor_id):
        response = supabase.table("servidores").select("*").eq("id", servidor_id).execute()
        if not response.data:
            return None
        registro = response.data[0]
        if "pais" in registro:
            registro["pais"] = self._normalize_country_name(registro["pais"])
        return self._decorate_server(registro)

    def atualizar_servidor(self, servidor_id, **kwargs):
        data = {}

        for key, value in kwargs.items():
            if key in ["nome", "capacidade_atual", "status"] and value is not None:
                data[key] = value

        normalized_pais = None
        indice = kwargs.get("indice")
        cidade = kwargs.get("cidade")

        if kwargs.get("pais") is not None:
            normalized_pais = self._normalize_country_name(kwargs.get("pais"))
            data["pais"] = normalized_pais

        if normalized_pais is None and (indice is not None or cidade):
            servidor_atual = self.listar_servidor_por_id(servidor_id)
            if servidor_atual and isinstance(servidor_atual, dict):
                pais_atual = servidor_atual.get("pais")
                if isinstance(pais_atual, str) and pais_atual.strip() != "":
                    normalized_pais = self._normalize_country_name(pais_atual)

        if normalized_pais is not None:
            if indice is None and cidade:
                indice = get_indice_cidade(normalized_pais, cidade)

            if not isinstance(indice, int):
                indice = 0

            data["latitude"] = get_latitude(normalized_pais, indice)
            data["longitude"] = get_longitude(normalized_pais, indice)
            data["continente"] = get_continente(normalized_pais)
            data["cidade"] = get_cidade(normalized_pais, indice)

        response = supabase.table("servidores").update(data).eq("id", servidor_id).execute()
        return [self._decorate_server(record) for record in response.data]

    def ativar_desativar_servidor(self, servidor_id, status):
        payload = {"status": status}
        if status:
            payload["reactivated_at"] = self._now_iso()
        else:
            payload["disabled_at"] = self._now_iso()

        try:
            response = supabase.table("servidores").update(payload).eq("id", servidor_id).execute()
        except Exception:
            response = supabase.table("servidores").update({"status": status}).eq("id", servidor_id).execute()
        return [self._decorate_server(record) for record in response.data]

    def buscar_servidores_por_pais(self, pais):
        pais = self._normalize_country_name(pais)
        response = supabase.table("servidores").select("*").eq("pais", pais).execute()
        return [self._decorate_server(record) for record in self._normalize_records_country(response.data)]

    def buscar_servidores_por_continente(self, continente):
        response = supabase.table("servidores").select("*").eq("continente", continente).execute()
        return [self._decorate_server(record) for record in self._normalize_records_country(response.data)]

    def buscar_servidor_por_nome(self, nome: str):
        response = supabase.table("servidores").select("id").ilike("nome", nome.strip()).execute()
        return response.data or []

    def listar_arquivos_por_servidor(self, servidor_id):
        response = (
            supabase.table("servidores_arquivos")
            .select("*")
            .eq("servidor_id", servidor_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data

    def adicionar_arquivo_servidor(self, servidor_id, titulo, descricao, tipo_arquivo, tamanho_gb):
        data = {
            "servidor_id": servidor_id,
            "titulo": titulo,
            "descricao": descricao,
            "tipo_arquivo": tipo_arquivo,
            "tamanho_gb": tamanho_gb,
            "created_at": self._now_iso(),
        }
        response = supabase.table("servidores_arquivos").insert(data).execute()
        return response.data

    def buscar_arquivo_por_id(self, arquivo_id):
        response = supabase.table("servidores_arquivos").select("*").eq("id", arquivo_id).execute()
        return response.data[0] if response.data else None

    def atualizar_arquivo_servidor(self, arquivo_id, **kwargs):
        data = {}
        for key, value in kwargs.items():
            if key in ["titulo", "descricao", "tipo_arquivo", "tamanho_gb"]:
                data[key] = value

        if not data:
            return None

        response = supabase.table("servidores_arquivos").update(data).eq("id", arquivo_id).execute()
        return response.data

    def excluir_arquivo_servidor(self, arquivo_id):
        response = supabase.table("servidores_arquivos").delete().eq("id", arquivo_id).execute()
        return response.data

    def excluir_servidor(self, servidor_id):
        self.excluir_arquivos_por_servidor(servidor_id)
        response = supabase.table("servidores").delete().eq("id", servidor_id).execute()
        return [self._decorate_server(record) for record in response.data]

    def excluir_arquivos_por_servidor(self, servidor_id):
        response = supabase.table("servidores_arquivos").delete().eq("servidor_id", servidor_id).execute()
        return response.data

    def _decorate_server(self, registro):
        if not isinstance(registro, dict):
            return registro

        registro["bandeira"] = self._get_country_flag(registro.get("pais"))
        return registro

    def _get_country_flag(self, pais_nome: str):
        if not pais_nome:
            return ""

        normalized = self._normalize_country_name(pais_nome)
        for paises in PAISES.values():
            for pais in paises:
                if self._normalize_country_name(pais.nome) == normalized:
                    return self._country_name_to_flag(pais.nome)
        return ""

    @staticmethod
    def _country_name_to_flag(pais_nome: str):
        country_codes = {
            "Brasil": "BR",
            "Argentina": "AR",
            "Colômbia": "CO",
            "Peru": "PE",
            "Chile": "CL",
            "Estados Unidos": "US",
            "Canadá": "CA",
            "México": "MX",
            "Costa Rica": "CR",
            "Panamá": "PA",
            "Alemanha": "DE",
            "França": "FR",
            "Reino Unido": "GB",
            "Itália": "IT",
            "Espanha": "ES",
            "Portugal": "PT",
            "China": "CN",
            "Índia": "IN",
            "Japão": "JP",
            "Nigéria": "NG",
            "Egito": "EG",
            "África do Sul": "ZA",
            "Austrália": "AU",
            "Nova Zelândia": "NZ",
        }
        code = country_codes.get(pais_nome)
        if not code:
            return ""
        return "".join(chr(127397 + ord(char)) for char in code)
