from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, chat, websocket
from app.routers.support import router as support_router
from app.database.connection import engine, SessionLocal
from app.models import user, room, message, member  # Import models to register them
from app.database.connection import Base
from sqlalchemy import text
import os

# Create UPLOADS folder
os.makedirs("static", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)

# Create Tables
Base.metadata.create_all(bind=engine)

# Auto-migration for schema changes (adding new columns)
try:
    with engine.begin() as conn:
        if "mysql" in engine.name:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_type VARCHAR(50) DEFAULT 'text';"))
            conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_url VARCHAR(1024) NULL;"))
            conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_name VARCHAR(255) NULL;"))
            conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_size INT NULL;"))
        else:
            # Fallback for SQLite testing environments
            for query in [
                "ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE messages ADD COLUMN message_type VARCHAR(50) DEFAULT 'text';",
                "ALTER TABLE messages ADD COLUMN file_url VARCHAR(1024) NULL;",
                "ALTER TABLE messages ADD COLUMN file_name VARCHAR(255) NULL;",
                "ALTER TABLE messages ADD COLUMN file_size INT NULL;"
            ]:
                try:
                    conn.execute(text(query))
                except Exception:
                    pass
except Exception as e:
    print(f"Auto-migration failed: {e}")

app = FastAPI(title="AIKYAM Connect")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, set to specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for attachments
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(auth.router, tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(support_router, prefix="/api", tags=["Support"])
app.include_router(websocket.router, tags=["WebSocket"])

@app.get("/")
async def root():
    return {"message": "RealTime Chat Backend Running"}