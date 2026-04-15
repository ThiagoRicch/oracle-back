from pydantic import BaseModel, Field
from typing import Optional


class ArquivoUpdateSchema(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=255)
    descricao: Optional[str] = Field(default=None, max_length=1000)
    tipo_arquivo: Optional[str] = Field(default=None, min_length=1, max_length=100)
    tamanho_gb: Optional[int] = Field(default=None, ge=1, le=10)
