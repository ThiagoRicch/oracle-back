from fastapi import APIRouter, HTTPException

from Schema.ArquivoCreateSchema import ArquivoCreateSchema
from Schema.ArquivoUpdateSchema import ArquivoUpdateSchema
from Schema.CapacitySchema import CapacitySchema
from Schema.ServidorCreateSchema import ServidorCreateSchema
from Schema.ServidorUpdateSchema import ServidorUpdateSchema
from Schema.StatusSchema import StatusSchema
from Service.ServidorService import ServidorService


router = APIRouter(prefix="/servidores", tags=["Servidores"])
service = ServidorService()


@router.get("/")
def listar_servidores():
    return service.listar()


@router.get("/{servidor_id}")
def listar_servidor_por_id(servidor_id: str):
    return service.listar_por_id(servidor_id)


@router.post("/")
def criar_servidor(servidor: ServidorCreateSchema):
    result = service.criar(servidor.nome, servidor.pais, servidor.indice)
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.put("/{servidor_id}")
def atualizar_servidor(servidor_id: str, servidor: ServidorUpdateSchema):
    result = service.atualizar(
        servidor_id,
        nome=servidor.nome,
        pais=servidor.pais,
        cidade=servidor.cidade,
        indice=servidor.indice,
    )
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.patch("/{servidor_id}/status")
def ativar_desativar_servidor(servidor_id: str, status: StatusSchema):
    return service.ativar_desativar(servidor_id, status.status)


@router.delete("/{servidor_id}")
def excluir_servidor(servidor_id: str):
    result = service.excluir(servidor_id)
    if isinstance(result, str):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.patch("/{servidor_id}/capacidade")
def adicionar_capacidade(servidor_id: str, capacidade: CapacitySchema):
    return service.adicionar_capacidade(servidor_id, capacidade.capacidade)


@router.get("/continentes/{continente}")
def listar_servidores_por_continente(continente: str):
    return service.listar_servidores_por_continente(continente)


@router.get("/paises/{pais}")
def listar_servidores_por_pais(pais: str):
    return service.listar_servidores_por_pais(pais)


@router.get("/{servidor_id}/arquivos")
def listar_arquivos_por_servidor(servidor_id: str):
    return service.listar_arquivos(servidor_id)


@router.post("/{servidor_id}/arquivos")
def adicionar_arquivo_no_servidor(servidor_id: str, arquivo: ArquivoCreateSchema):
    result = service.adicionar_arquivo(
        servidor_id=servidor_id,
        titulo=arquivo.titulo,
        descricao=arquivo.descricao,
        tipo_arquivo=arquivo.tipo_arquivo,
        tamanho_gb=arquivo.tamanho_gb,
    )

    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.patch("/{servidor_id}/arquivos/{arquivo_id}")
def atualizar_arquivo_do_servidor(servidor_id: str, arquivo_id: str, arquivo: ArquivoUpdateSchema):
    result = service.atualizar_arquivo(
        servidor_id=servidor_id,
        arquivo_id=arquivo_id,
        titulo=arquivo.titulo,
        descricao=arquivo.descricao,
        tipo_arquivo=arquivo.tipo_arquivo,
        tamanho_gb=arquivo.tamanho_gb,
    )

    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.delete("/{servidor_id}/arquivos/{arquivo_id}")
def excluir_arquivo_do_servidor(servidor_id: str, arquivo_id: str):
    result = service.excluir_arquivo(servidor_id=servidor_id, arquivo_id=arquivo_id)

    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)

    return result
