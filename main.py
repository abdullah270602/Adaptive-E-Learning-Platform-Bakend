import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from app.constants import ALLOWED_ORIGINS
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.routes.file import router as file_router
from app.routes.auth import router as auth_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

load_dotenv(override=True)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY")
)


@app.get("/")
def read_root():
    return {"FYP Backend": "Online 👍"}


app.include_router(file_router)
app.include_router(auth_router)