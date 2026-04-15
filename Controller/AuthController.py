from fastapi import APIRouter
from Schema.LoginSchema import LoginSchema
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(dados: LoginSchema):
    if dados.senha == os.getenv("APP_PASSWORD"):
        return {"autenticado": True}
    return {"autenticado": False}