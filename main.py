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

frontend_url = os.getenv("FRONTEND_URL", "https://oracle-pim.vercel.app").rstrip("/")
allow_origins = [frontend_url]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
