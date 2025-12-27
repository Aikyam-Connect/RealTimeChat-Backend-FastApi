from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.schemas import schemas
from app.core import security
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
    return user

@router.post("/login/google", response_model=schemas.Token)
def login_google(login_data: schemas.GoogleLogin, db: Session = Depends(get_db)):
    # Verify Google Token
    google_data = security.verify_google_token(login_data.credential)
    if not google_data:
         raise HTTPException(status_code=400, detail="Invalid Google Token")
    
    email = google_data.get("email")
    name = google_data.get("name")
    picture = google_data.get("picture")
    google_id = google_data.get("sub")

    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create new user
        user = User(email=email, name=name, picture=picture, google_id=google_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update info if changed (optional)
        user.name = name
        user.picture = picture
        db.commit()

    # Create access token
    access_token_expires = security.timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user