from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.core.config import settings
from google.oauth2 import id_token
from google.auth.transport import requests

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_google_token(token: str):
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        # Or, if multiple clients access the backend server:
        # id_info = id_token.verify_oauth2_token(token, requests.Request())
        # if id_info['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, ...]:
        #     raise ValueError('Could not verify audience.')

        # If auth request is from a G Suite domain:
        # if id_info['hd'] != GSUITE_DOMAIN_NAME:
        #     raise ValueError('Wrong hosted domain.')

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        return id_info
    except ValueError as e:
        # Invalid token
        print(f"Error verifying google token: {e}")
        return None

import hashlib
import os

CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dh901hnb9")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "297566653823482")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "ofq4-6BmhjGXMj0zz1wuYSdEfmY")

def generate_cloudinary_signature(params: dict) -> str:
    # Sort parameters alphabetically
    sorted_params = sorted(params.items())
    # Create the query string
    param_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    # Append the API Secret
    sign_str = param_str + CLOUDINARY_API_SECRET
    # Return SHA-1 digest in hex format
    return hashlib.sha1(sign_str.encode('utf-8')).hexdigest()