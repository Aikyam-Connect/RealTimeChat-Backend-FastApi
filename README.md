# FastAPI RealTime Chat Backend

Full-stack Real-Time Chat Application Backend using FastAPI, PostgreSQL, and WebSockets.

## Features

- **Google Authentication** (No password login).
- **Real-Time Chat** using native WebSockets.
- **Room/Group Management**: Create rooms, join rooms.
- **Video/Audio Calls**: WebRTC Signaling over WebSockets (Mesh Network).
- **PostgreSQL Database** with SQLAlchemy ORM.

## Setup

1.  **Clone the repository**.
2.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configuration**:
    - Update `.env` file with your PostgreSQL credentials and Google Client ID.
    ```env
    DATABASE_URL=postgresql+psycopg2://user:password@localhost/dbname
    GOOGLE_CLIENT_ID=your-google-client-id
    SECRET_KEY=your-secret-key
    ```
5.  **Run the Server**:
    ```bash
    uvicorn app.main:app --reload
    ```
    The server will start at `http://127.0.0.1:8000`.
    API Documentation: `http://127.0.0.1:8000/docs`.

## API Endpoints

- `POST /login/google`: Authenticate with Google Token.
- `GET /users/me`: Get current user info.
- `GET /api/rooms`: Get my rooms.
- `POST /api/rooms`: Create a new room.
- `GET /api/rooms/{id}/messages`: Get room history.
- `WS /ws?token={jwt}`: WebSocket connection for Chat and WebRTC.
