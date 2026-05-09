import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware import Middleware

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


# CORS configurado no construtor via Middleware — forma mais confiavel em
# FastAPI + gunicorn/uvicorn, evita o problema de add_middleware ser
# ignorado quando registrado apos include_router.
app = FastAPI(
    lifespan=lifespan,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)


# Segunda camada de CORS: middleware HTTP manual que garante o header
# Access-Control-Allow-Origin em TODA resposta, inclusive erros nao
# tratados que possam escapar do CORSMiddleware.
@app.middleware("http")
async def force_cors(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            },
        )
    try:
        response = await call_next(request)
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("Erro nao tratado na requisicao: %s", exc)
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


app.include_router(auth_router)
app.include_router(servidor_router)
app.include_router(geografia_router)
app.include_router(internal_jobs_router)
