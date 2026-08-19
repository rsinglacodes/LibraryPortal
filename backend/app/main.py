import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import Base, get_engine
from app.models import User, Book, Rating, UserInteraction
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.books import router as books_router
from app.routes.borrows import router as borrows_router
from app.routes.chat import router as chat_router
from app.routes.ratings import router as ratings_router
from app.routes.recommendations import router as recommendations_router

app = FastAPI(
    title="LibraryPortal API",
    description="Backend API for the University Library Portal",
    version="0.1.0",
)

@app.on_event("startup")
def on_startup():
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Startup DB init warning: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Support both root and /api prefixed routes
app.include_router(auth_router)
app.include_router(auth_router, prefix="/api")

app.include_router(books_router)
app.include_router(books_router, prefix="/api")

app.include_router(chat_router)
app.include_router(chat_router, prefix="/api")

app.include_router(ratings_router)
app.include_router(ratings_router, prefix="/api")

app.include_router(recommendations_router)
app.include_router(recommendations_router, prefix="/api")

app.include_router(borrows_router)
app.include_router(borrows_router, prefix="/api")

app.include_router(admin_router)
app.include_router(admin_router, prefix="/api")



@app.get("/health")
def health_check():
    return {"status": "ok"}
