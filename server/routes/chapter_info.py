from fastapi import APIRouter, Request, HTTPException
from supabase import create_client, Client
import os


db : Client = create_client(supabase_key=os.getenv("SUPABASE_KEY"), supabase_url=os.getenv("SUPABASE_URL"))

db_router = APIRouter(prefix="/api/db")

@db_router.get("/get-chapters")
async def get_chapters():
    try:    
        data = (
            db.table("chunks")
            .select("chapter_name", "subject", "standard")
            .execute()
        )
        return {"chapters" : data.data}

    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
