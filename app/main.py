from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, chat, websocket
from app.database.connection import engine
from app.models import user, room, message, member  # Import models to register them
from app.database.connection import Base

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RealTimeChat")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, set to specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(websocket.router, tags=["WebSocket"])

@app.get("/")
async def root():
    return {"message": "RealTime Chat Backend Running"}