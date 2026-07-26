from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from src.base_settings import settings


MAIN_AI_MODEL = "gemini-3.5-flash"
SUPABASE_KEY=settings.SUPABASE_KEY
SUPABASE_SERVICE_ROLE_KEY=settings.SUPABASE_SERVICE_ROLE_KEY
SUPABASE_URL=settings.SUPABASE_URL


ALTERNATE_GOOGLE_AI_MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash"]
ALTERNATE_GROQ_MODELS = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"]


model_list = [ChatGoogleGenerativeAI(
    temperature=0.1,
    model=model_name,
    google_api_key=settings.GOOGLE_API_KEY,
    max_retries=2,
    thinking_level="medium"
) for model_name in ALTERNATE_GOOGLE_AI_MODELS]


model_list.extend([
    ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=model_name,
        max_retries=2,
        temperature=0.1,
        reasoning_effort="default"
    ) 
    
    for model_name in ALTERNATE_GROQ_MODELS   
])


generator_model = ChatGoogleGenerativeAI(
    temperature=0.1,
    model=MAIN_AI_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    max_retries=2,
    thinking_level="medium"
)

generator_model = generator_model.with_fallbacks(model_list)



CHUNK_BATCH_SIZE=5