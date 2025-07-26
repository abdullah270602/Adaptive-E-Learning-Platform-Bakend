import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from app.constants import ALLOWED_ORIGINS
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.routes.file import router as file_router
from app.routes.auth import router as auth_router
from app.routes.learning_profile import router as learning_profile_router
from app.routes.models import router as models_router
from app.routes.study_mode import router as study_mode_router
from app.routes.streaks import router as streaks_router
from app.routes.transcribe import router as transcribe_router
from app.routes.library_search import router as library_search_router
from app.routes.quiz_gen import router as quiz_gen_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

load_dotenv(dotenv_path=".env")
app = FastAPI(
    title="Adaptive Learn AI Backend",
    description="Backend for Adaptive Learn AI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
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


@app.on_event("startup")
async def load_models_to_cache_event():
    from app.database.connection import PostgresConnection
    from app.cache.models import load_models_to_cache
    with PostgresConnection() as conn:
        try:
            load_models_to_cache(conn)
        except Exception as e:
            logging.error(f" Failed to load models to cache: {e}")

app.include_router(file_router)
app.include_router(auth_router)
app.include_router(learning_profile_router)
app.include_router(models_router)
app.include_router(study_mode_router)
app.include_router(streaks_router)
app.include_router(transcribe_router)
app.include_router(library_search_router)
app.include_router(quiz_gen_router)
