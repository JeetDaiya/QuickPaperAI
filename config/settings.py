from langchain_openrouter import ChatOpenRouter
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os

load_dotenv()

AI_MODEL = "gemini-3.1-flash-lite"
SUPABASE_KEY=os.getenv("SUPABASE_KEY")
SUPABASE_URL=os.getenv("SUPABASE_URL")


generator_model = ChatGoogleGenerativeAI(
    temperature=0.1,
    model=AI_MODEL,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    max_retries=2,
    thinking_level="high"
)


CHUNK_BATCH_SIZE=5