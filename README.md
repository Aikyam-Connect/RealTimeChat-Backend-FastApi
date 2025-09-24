# FastAPI Backend for Group Project

## Overview

Backend API using FastAPI with:

- User registration & JWT authentication  
- Real-time WebSocket communication  
- Room creation API  

## Setup

1. Clone repo and enter directory  
2. Create & activate virtual environment
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
    ```
3. Install dependencies:  
   `pip install -r requirements.txt`  
4. Create `.env` with your config (e.g., database URL, secret key)  
5. Start server:  
   `uvicorn app.main:app --reload`  
6. Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for API docs  

## Testing

Run tests with:  
`pytest`

---
