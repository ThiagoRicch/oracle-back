from pydantic import BaseModel

class LoginSchema(BaseModel):
    senha: str
