import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes_chat import router as chat_router
from api.routes_metrics import router as metrics_router
from api.routes_library import router as library_router

app = FastAPI(title="PaceAlyzer Backend", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "Hello!"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://pacealyzer.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(library_router, prefix="/api")
