from config.settings import SUPABASE_KEY, SUPABASE_URL
from supabase import create_client, Client



db : Client = create_client(supabase_key=SUPABASE_KEY, supabase_url=SUPABASE_URL)


def get_chapter_chunks(subject: str, chapter : str) -> list[dict]:
    response = (
        db.table("chunks")
        .select("*")
        .eq("chapter_name", chapter)
        .eq("subject", subject)
        .order("chunk_index")
        .execute()
    )
    
    paper_chunks = response.data
    
    return paper_chunks