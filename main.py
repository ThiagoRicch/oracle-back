from fastapi import FastAPI
from Controller.ServidorController import router as servidor_router
from Controller.AuthController import router as auth_router
from Controller.GeografiaController import router as geografia_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(auth_router)
app.include_router(servidor_router)
app.include_router(geografia_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # em produção coloca a URL do frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

