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
