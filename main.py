from fastapi import FastAPI
from Controller.ServidorController import router as servidor_router
from Controller.AuthController import router as auth_router
from Controller.GeografiaController import router as geografia_router
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.include_router(auth_router)
app.include_router(servidor_router)
app.include_router(geografia_router)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

