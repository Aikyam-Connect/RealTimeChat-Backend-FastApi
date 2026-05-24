from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from app.database.connection import get_db
from app.models.user import User
from app.models.room import Room
from app.models.member import Member
from app.models.message import Message
from app.schemas import schemas
from app.core import security
from app.services.websocket_manager import manager
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
import requests
import time
import json
import io
import zipfile
from datetime import datetime, timedelta

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Cloudinary Destroy Helper
def delete_from_cloudinary(public_id: str, resource_type: str):
    timestamp = int(time.time())
    params = {
        "public_id": public_id,
        "timestamp": timestamp
    }
    signature = security.generate_cloudinary_signature(params)
    data = {
        "public_id": public_id,
        "api_key": security.CLOUDINARY_API_KEY,
        "timestamp": timestamp,
        "signature": signature
    }
    url = f"https://api.cloudinary.com/v1_1/{security.CLOUDINARY_CLOUD_NAME}/{resource_type}/destroy"
    try:
        res = requests.post(url, data=data)
        print(f"Cloudinary destroy result: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Error destroying Cloudinary asset: {e}")

# Dependency to check if support user (admin flag check)
def get_current_support_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
        
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Email not authorized for Support access."
        )
        
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Your account has been banned.")
        
    return user

# Support Login
@router.post("/support/login", response_model=schemas.Token)
def support_login(login_data: schemas.GoogleLogin, db: Session = Depends(get_db)):
    google_data = security.verify_google_token(login_data.credential)
    if not google_data:
         raise HTTPException(status_code=400, detail="Invalid Google Token")
    
    email = google_data.get("email")
    name = google_data.get("name")
    picture = google_data.get("picture")
    google_id = google_data.get("sub")

    # Ensure user exists in users table and is_admin is true
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Your email is not authorized for support console access."
        )
        
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Your account has been banned.")
        
    user.name = name
    user.picture = picture
    db.commit()

    access_token_expires = security.timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Analytics Dashboard Stats
@router.get("/support/analytics")
def get_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    total_users = db.query(User).count()
    online_users = len(manager.active_connections)
    active_rooms = db.query(Room).count()
    
    # Calculate storage usage
    messages_with_files = db.query(Message).filter(Message.file_url != None).all()
    storage_bytes = sum([m.file_size for m in messages_with_files if m.file_size])
    storage_str = f"{storage_bytes / (1024*1024):.2f} MB" if storage_bytes else "0.00 MB"
    
    # Messages sent today
    today = datetime.utcnow().date()
    messages_today = db.query(Message).filter(Message.created_at >= today).count()
    
    # Simple growth analytics
    users_list = db.query(User).order_by(User.created_at).all()
    growth_chart = {}
    for u in users_list:
        month = u.created_at.strftime("%Y-%m")
        growth_chart[month] = growth_chart.get(month, 0) + 1

    return {
        "total_users": total_users,
        "online_users": online_users,
        "messages_today": messages_today,
        "active_rooms": active_rooms,
        "storage_usage": storage_str,
        "storage_bytes": storage_bytes,
        "growth": [{"month": k, "count": v} for k, v in growth_chart.items()]
    }

# View Users
@router.get("/support/users", response_model=List[schemas.User])
def get_all_users_admin(db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    return db.query(User).all()

# Ban User
@router.post("/support/users/{user_id}/ban")
async def ban_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_banned = True
    db.commit()
    
    # Force disconnect user from WebSocket
    if user_id in manager.active_connections:
        try:
            await manager.active_connections[user_id].close(code=4003)
        except Exception:
            pass
        manager.disconnect(user_id)
        
    return {"message": f"User {user.name} banned successfully"}

# Unban User
@router.post("/support/users/{user_id}/unban")
def unban_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_banned = False
    db.commit()
    return {"message": f"User {user.name} unbanned successfully"}

# View Rooms
@router.get("/support/rooms", response_model=List[schemas.RoomResponse])
def get_rooms_admin(db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    return db.query(Room).all()

# View Messages in Room
@router.get("/support/rooms/{room_id}/messages", response_model=List[schemas.MessageResponse])
def get_room_messages_admin(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    messages = db.query(Message).filter(Message.room_id == room_id).order_by(Message.created_at).all()
    results = []
    for msg in messages:
        msg_resp = schemas.MessageResponse.from_orm(msg)
        msg_resp.sender_name = msg.sender.name if msg.sender else "Unknown"
        results.append(msg_resp)
    return results

# Delete Message & Cloudinary Attachment
@router.delete("/support/messages/{message_id}")
def delete_message_admin(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    # Check if there is Cloudinary attachment
    if msg.file_url and msg.file_name and "|" in msg.file_name:
        try:
            parts = msg.file_name.split("|")
            if len(parts) >= 3:
                public_id = parts[1]
                resource_type = parts[2]
                delete_from_cloudinary(public_id, resource_type)
        except Exception as e:
            print(f"Failed to delete Cloudinary asset: {e}")
            
    db.delete(msg)
    db.commit()
    return {"message": "Message and associated media deleted successfully"}

# Backup Database as ZIP containing JSON tables
@router.post("/support/maintenance/backup")
def get_backup_zip(db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    # Export Tables
    users = [dict(id=u.id, email=u.email, name=u.name, picture=u.picture, is_banned=u.is_banned, is_admin=u.is_admin, created_at=str(u.created_at)) for u in db.query(User).all()]
    rooms = [dict(id=r.id, name=r.name, is_group=r.is_group, created_by=r.created_by, created_at=str(r.created_at)) for r in db.query(Room).all()]
    members = [dict(id=m.id, room_id=m.room_id, user_id=m.user_id, joined_at=str(m.joined_at)) for m in db.query(Member).all()]
    messages = [dict(id=msg.id, content=msg.content, sender_id=msg.sender_id, room_id=msg.room_id, message_type=msg.message_type, file_url=msg.file_url, file_name=msg.file_name, file_size=msg.file_size, created_at=str(msg.created_at)) for msg in db.query(Message).all()]

    # Create Zip File in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("users.json", json.dumps(users, indent=2))
        zip_file.writestr("rooms.json", json.dumps(rooms, indent=2))
        zip_file.writestr("members.json", json.dumps(members, indent=2))
        zip_file.writestr("messages.json", json.dumps(messages, indent=2))
        
    zip_buffer.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="aikyam_connect_backup.zip"'
    }
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)

# Maintenance Database Cleanup
@router.post("/support/maintenance/cleanup")
def perform_cleanup(older_than_days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_support_user)):
    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
    
    # Find old messages with attachments
    old_messages = db.query(Message).filter(Message.created_at < cutoff_date).all()
    cleaned_count = 0
    cloudinary_cleaned = 0
    
    for msg in old_messages:
        # Check and delete from Cloudinary
        if msg.file_url and msg.file_name and "|" in msg.file_name:
            try:
                parts = msg.file_name.split("|")
                if len(parts) >= 3:
                    delete_from_cloudinary(parts[1], parts[2])
                    cloudinary_cleaned += 1
            except Exception:
                pass
        db.delete(msg)
        cleaned_count += 1
        
    db.commit()
    return {
        "message": "Cleanup completed",
        "deleted_messages_count": cleaned_count,
        "cloudinary_assets_destroyed": cloudinary_cleaned
    }
