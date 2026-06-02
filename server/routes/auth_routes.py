from server.schemas.user_schemas import UserLogin, UserRegister, UserResponse
from server.schemas.token_schemas import Token, TokenData
from fastapi import APIRouter, HTTPException, status, Depends
from server.core.security import create_access_token, get_password_hash, verify_password
from server.db import get_user, create_user
from fastapi.security import OAuth2PasswordRequestForm

auth_routes = APIRouter(prefix='/auth')



@auth_routes.post('/register', response_model=UserResponse)
def register_user(user: UserRegister):
    user_email = user.email
    db_user = get_user(email=user_email)
    
    if db_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    else:
        password = user.password
        hashed_password = get_password_hash(plain_password=password)
        user_name = user.name
        new_user = create_user(email=user_email, hashed_password=hashed_password, name=user_name)
        return new_user

@auth_routes.post('/login', response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(email=form_data.username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")    

    password = form_data.password
    if not verify_password(plain_password=password, hashed_password=user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user["email"]})
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }