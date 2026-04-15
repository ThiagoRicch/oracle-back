from pydantic import BaseModel, Field
from typing import Optional


class ArquivoCreateSchema(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    descricao: Optional[str] = Field(default=None, max_length=1000)
    tipo_arquivo: str = Field(min_length=1, max_length=100)
    tamanho_gb: int = Field(ge=1, le=10)
