from supabase import create_client, Client
import os
from pydantic import EmailStr

db: Client = create_client(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

def get_user(email: EmailStr):
    data = db.table("users").select("*").eq("email", email).execute()
    return data.data[0] if data.data else None

def create_user(email: str, hashed_password: str, name: str):
    user_data = {
        "email": email,
        "hashed_password": hashed_password,
        "name": name,
        "is_active" : False
    }
    response = db.table("users").insert(user_data).execute()
    return response.data[0] if response.data else None

def update_user_password(email: str, new_hashed_password: str):
    response = db.table("user").update({"hashed_password" : new_hashed_password}).eq("email" , email).execute()
    return response.data[0] if response.data else None