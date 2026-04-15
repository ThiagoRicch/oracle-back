from pydantic import BaseModel
from typing import Optional

class ServidorUpdateSchema(BaseModel):
    nome: Optional[str] = None
    pais: Optional[str] = None
    cidade: Optional[str] = None
    indice: Optional[int] = None