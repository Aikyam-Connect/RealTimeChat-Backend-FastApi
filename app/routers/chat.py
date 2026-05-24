from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.user import User
from app.models.room import Room
from app.models.member import Member
from app.models.message import Message
from app.schemas import schemas
from app.routers.auth import get_current_user

router = APIRouter()

@router.post("/rooms", response_model=schemas.RoomResponse)
def create_room(room: schemas.RoomCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_room = Room(name=room.name, is_group=room.is_group, created_by=current_user.id)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    # Add creator as member
    member = Member(room_id=new_room.id, user_id=current_user.id)
    db.add(member)
    db.commit()
    
    return new_room

@router.get("/rooms", response_model=List[schemas.RoomResponse])
def get_my_rooms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memberships = db.query(Member).filter(Member.user_id == current_user.id).all()
    room_ids = [m.room_id for m in memberships]
    rooms = db.query(Room).filter(Room.id.in_(room_ids)).all()
    return rooms

@router.get("/rooms/{room_id}/messages", response_model=List[schemas.MessageResponse])
def get_messages(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if member
    membership = db.query(Member).filter(Member.room_id == room_id, Member.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    messages = db.query(Message).filter(Message.room_id == room_id).order_by(Message.created_at).all()
    
    # Enrich with sender name
    results = []
    for msg in messages:
        msg_resp = schemas.MessageResponse.from_orm(msg)
        msg_resp.sender_name = msg.sender.name if msg.sender else "Unknown"
        results.append(msg_resp)
        
    return results

@router.post("/rooms/{room_id}/join")
def join_room(room_id: int, user_id_to_add: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if current user is member (or allow anyone to join if public? Let's restrict to 'invite' style implies adding others)
    # The requirement said "manage everything like room group".
    # Let's allow adding other users by ID/Email. For simplicity, let's assume we pass user_id_to_add.
    
    membership = db.query(Member).filter(Member.room_id == room_id, Member.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member")
        
    # Check if already added
    exists = db.query(Member).filter(Member.room_id == room_id, Member.user_id == user_id_to_add).first()
    if not exists:
        new_member = Member(room_id=room_id, user_id=user_id_to_add)
        db.add(new_member)
        db.commit()
        
    return {"message": "User added"}

@router.get("/users", response_model=List[schemas.User])
def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # For finding people to add
    return db.query(User).all()

@router.post("/rooms/direct", response_model=schemas.RoomResponse)
def get_or_create_direct_room(target_user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if a 1-to-1 room already exists between current_user and target_user_id
    # Find all room IDs that the current user is in
    my_room_ids = db.query(Member.room_id).filter(Member.user_id == current_user.id).subquery()
    
    # Find if there is a room from those IDs that is direct (not group) and contains the target user
    existing_direct_member = db.query(Member).join(Room, Room.id == Member.room_id).filter(
        Member.room_id.in_(my_room_ids),
        Member.user_id == target_user_id,
        Room.is_group == False
    ).first()
    
    if existing_direct_member:
        # Return that room
        return db.query(Room).filter(Room.id == existing_direct_member.room_id).first()
        
    # Otherwise, create a new direct room
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
        
    new_room = Room(name=f"Direct: {current_user.name} & {target_user.name}", is_group=False, created_by=current_user.id)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    
    # Add both users as members
    m1 = Member(room_id=new_room.id, user_id=current_user.id)
    m2 = Member(room_id=new_room.id, user_id=target_user_id)
    db.add_all([m1, m2])
    db.commit()
    
    return new_room

@router.get("/rooms/{room_id}/members", response_model=List[schemas.User])
def get_room_members(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verify current user is a member of the room
    membership = db.query(Member).filter(Member.room_id == room_id, Member.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this room")
        
    # Retrieve all users in the room
    members = db.query(User).join(Member, Member.user_id == User.id).filter(Member.room_id == room_id).all()
    return members

from fastapi import UploadFile, File
import time
import requests
import os
from app.core import security

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    file_bytes = await file.read()
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    # Map resource types for Cloudinary
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"]:
        resource_type = "image"
    elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".ogg", ".m4a", ".aac"]:
        resource_type = "video"
    else:
        resource_type = "raw"
        
    timestamp = int(time.time())
    params = {
        "folder": "aikyam_connect",
        "timestamp": timestamp
    }
    signature = security.generate_cloudinary_signature(params)
    
    # Prepare payload for Cloudinary API
    files = {
        "file": (filename, file_bytes)
    }
    data = {
        "api_key": security.CLOUDINARY_API_KEY,
        "timestamp": timestamp,
        "folder": "aikyam_connect",
        "signature": signature
    }
    
    url = f"https://api.cloudinary.com/v1_1/{security.CLOUDINARY_CLOUD_NAME}/{resource_type}/upload"
    try:
        response = requests.post(url, files=files, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {response.text}")
        res_data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed uploading to Cloudinary: {str(e)}")
        
    # Get secure URL, public ID, and size
    file_url = res_data.get("secure_url")
    public_id = res_data.get("public_id")
    file_size = res_data.get("bytes", len(file_bytes))
    
    # Return formatted details
    return {
        "file_url": file_url,
        "file_name": f"{filename}|{public_id}|{resource_type}",
        "file_size": file_size
    }


