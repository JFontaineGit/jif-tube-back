from fastapi import FastAPI, Request, APIRouter, Header, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from contextlib import asynccontextmanager

from pathlib import Path

from typing import Dict, Optional, List

from app.db import init_db, SessionDep
from app.models import User
from app.auth import auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield None
    pass

app = FastAPI(
    title="Jif-Tube-API",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SPAStatic(StaticFiles):
    def __init__(self, directory:Path, html:bool=True, check_dir:bool=True, index_html:Path = Path("index.html")):
        super().__init__(directory=directory, html=html, check_dir=check_dir)
        self.index_html = index_html

        self.app = super.__call__

    async def __call__(self, scope, receive, send):

        assert scope["type"] == "http"

        request = Request(scope, receive)

        path = request.url.path.lstrip("/")

        if request.url.path.startswith("/api"):
            await self.app(scope, receive, send)
            return None

        full_path = (Path(self.directory) / path).resolve()

        if full_path.exists():
            await self.app(scope, receive, send)
            return None

        index_path = Path(self.directory) / self.index_html
        response = FileResponse(index_path)

        return response(scope, receive, send)

# Incluir el router de autenticación
app.include_router(auth_router)

# Endpoint de prueba
@app.get("/")
async def root():
    return {"message": "Jif-Tube API is running!"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "API is running correctly"}