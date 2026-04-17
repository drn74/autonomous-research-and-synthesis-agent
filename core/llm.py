import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from core.config import APP_CONFIG

# Ensure environment variables are loaded
load_dotenv()

def get_gemini_api_key():
    """Retrieves the GEMINI_API_KEY from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Fallback to GOOGLE_API_KEY if GEMINI is not found
        api_key = os.getenv("GOOGLE_API_KEY")
    return api_key

def get_gemini_model(purpose: str = "planner", temperature: float = 0.2):
    """
    Returns an instance of the Gemini model based on the purpose defined in config.json.
    Purposes: 'planner', 'synthesizer', 'domain_detector', 'critic'
    """
    model_key = purpose if purpose in APP_CONFIG.get("models", {}) else "planner"
    model_name = APP_CONFIG.get("models", {}).get(model_key, "gemini-2.5-flash")
    api_key = get_gemini_api_key()
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=2,
        google_api_key=api_key
    )

def get_gemini_embeddings():
    """
    Returns an instance of the Gemini embeddings model.
    """
    api_key = get_gemini_api_key()
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=api_key
    )
