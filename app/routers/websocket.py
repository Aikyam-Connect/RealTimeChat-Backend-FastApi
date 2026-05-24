from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.websocket_manager import manager
from app.core import security
from jose import jwt, JWTError
from app.models.user import User
from app.models.message import Message
from app.models.member import Member
from app.schemas import schemas
import json

router = APIRouter()

async def get_current_user_ws(token: str, db: Session):
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.email == email).first()
    return user

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(...), 
    db: Session = Depends(get_db)
):
    user = await get_current_user_ws(token, db)
    if user is None:
        await websocket.close(code=4001) # Unauthorized
        return

    await manager.connect(websocket, user.id)
    try:
        while True:
            data = await websocket.receive_json()
            # Expected data format: { "type": "...", "content": "...", "roomId": 1, ... }
            
            message_type = data.get("type")

            if message_type == "chat":
                room_id = data.get("roomId")
                content = data.get("content")
                msg_type = data.get("msgType", "text")
                file_url = data.get("fileUrl")
                file_name = data.get("fileName")
                file_size = data.get("fileSize")

                if room_id and (content or file_url):
                    # Save Message
                    new_msg = Message(
                        content=content or "", 
                        sender_id=user.id, 
                        room_id=room_id,
                        message_type=msg_type,
                        file_url=file_url,
                        file_name=file_name,
                        file_size=file_size
                    )
                    db.add(new_msg)
                    db.commit()
                    db.refresh(new_msg)

                    # Get Room Members
                    members = db.query(Member).filter(Member.room_id == room_id).all()
                    member_ids = [m.user_id for m in members]

                    # Broadcast
                    response_msg = {
                        "type": "new_message",
                        "message": {
                            "id": new_msg.id,
                            "content": new_msg.content,
                            "sender_id": new_msg.sender_id,
                            "room_id": new_msg.room_id,
                            "message_type": new_msg.message_type,
                            "file_url": new_msg.file_url,
                            "file_name": new_msg.file_name,
                            "file_size": new_msg.file_size,
                            "created_at": new_msg.created_at.isoformat(),
                            "sender_name": user.name
                        }
                    }
                    await manager.broadcast(response_msg, member_ids)

            elif message_type == "typing":
                room_id = data.get("roomId")
                is_typing = data.get("isTyping", False)
                if room_id:
                    # Broadcast typing state to other members
                    members = db.query(Member).filter(Member.room_id == room_id).all()
                    member_ids = [m.user_id for m in members if m.user_id != user.id]
                    await manager.broadcast({
                        "type": "typing",
                        "senderId": user.id,
                        "senderName": user.name,
                        "roomId": room_id,
                        "isTyping": is_typing
                    }, member_ids)

            elif message_type in ["offer", "answer", "candidate", "reject_call", "cancel_call", "end_call"]:
                # WebRTC Signaling & Call Controls
                target_id = data.get("targetId")
                if target_id:
                    # Forward directly to target
                    data["senderId"] = user.id # Attach sender ID so receiver knows who sent it
                    await manager.send_personal_message(data, target_id)
            
            elif message_type == "call_user":
                 target_id = data.get("targetId")
                 media_type = data.get("mediaType", "video")
                 if target_id:
                      await manager.send_personal_message({
                          "type": "incoming_call", 
                          "callerId": user.id, 
                          "callerName": user.name,
                          "mediaType": media_type,
                          "roomId": data.get("roomId", 0) # Optional room context
                      }, target_id)

            elif message_type == "accept_call":
                target_id = data.get("targetId")
                if target_id:
                      await manager.send_personal_message({
                          "type": "call_accepted", 
                          "acceptorId": user.id
                      }, target_id)
            
    except WebSocketDisconnect:
        manager.disconnect(user.id)
        # Maybe notify others?
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(user.id)