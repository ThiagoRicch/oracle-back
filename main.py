import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Controller.AuthController import router as auth_router
from Controller.GeografiaController import router as geografia_router
from Controller.InternalJobsController import router as internal_jobs_router
from Controller.ServidorController import router as servidor_router
from Service.SchedulerService import scheduler_service


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start()
    yield
    scheduler_service.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(servidor_router)
app.include_router(geografia_router)
app.include_router(internal_jobs_router)

# CORS — aceita multiplas origens separadas por virgula em FRONTEND_URL,
# e sempre inclui defaults conhecidos (Vercel de producao + dev local) para
# evitar lockout caso a variavel de ambiente seja apagada/alterada por engano.
_frontend_env = os.getenv("FRONTEND_URL", "")
_env_origins = [u.strip().rstrip("/") for u in _frontend_env.split(",") if u.strip()]

_default_origins = [
    "https://oracle-pim.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

allow_origins: list[str] = []
for origin in _env_origins + _default_origins:
    if origin and origin not in allow_origins:
        allow_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    # Libera previews do Vercel (oracle-pim-<hash>-<usuario>.vercel.app)
    allow_origin_regex=r"https://oracle-pim(-[a-z0-9-]+)?\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)
