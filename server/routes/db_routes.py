from fastapi import APIRouter, Depends, Request, HTTPException
from server.db import db
import os

from server.dependencies import get_current_user


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
        raise HTTPException(status_code=500, detail=str(e))

@db_router.get("/history")
async def get_history(current_user : dict = Depends(get_current_user)):
    try:
        user_id = str(current_user["id"])
        # Query generated papers sorted by created_at DESC
        res = (
            db.table("generated_papers")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        
        history_list = []
        for row in res.data:
            thread_id = row.get("thread_id")
            history_list.append({
                "id": row.get("id"),
                "thread_id": thread_id,
                "created_at": row.get("created_at"),
                "institution_name": row.get("institution_name"),
                "subject": row.get("subject"),
                "standard": row.get("standard"),
                "difficulty": row.get("difficulty"),
                "chapters": row.get("chapters"),
                "objective_count": row.get("objective_count", 0),
                "subjective_count": row.get("subjective_count", 0),
                "allowed_types": row.get("allowed_types", []),
                # Map raw Supabase paths to server-proxied download routes
                "paper_pdf": f"/api/download/{thread_id}/paper.pdf",
                "paper_docx": f"/api/download/{thread_id}/paper.docx",
                "answer_pdf": f"/api/download/{thread_id}/answer.pdf"
            })
            
        return {"history": history_list}
        
    except Exception as e:
        print(f"❌ Error fetching paper history: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to load paper history: {str(e)}"
        )
