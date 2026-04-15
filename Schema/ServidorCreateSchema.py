from pydantic import BaseModel
from typing import Optional

class ServidorCreateSchema(BaseModel):
    nome: str
    pais: str
    indice: Optional[int] = None