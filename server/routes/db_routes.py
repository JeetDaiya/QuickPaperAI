from fastapi import APIRouter, Request, HTTPException
from server.db import db
import os


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
async def get_history():
    
    dummy_user_id = os.getenv("DUMMY_USER_ID", "550e8400-e29b-41d4-a716-446655440000").strip('"')
    
    try:
        # Query generated papers sorted by created_at DESC
        res = (
            db.table("generated_papers")
            .select("*")
            .eq("user_id", dummy_user_id)
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
