import os
from dotenv import load_dotenv

load_dotenv()



SECRET_KEY = os.getenv("SECRET_KEY") 

ALGORITHM = "HS256" # JWT hashing algoritm

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days expiry