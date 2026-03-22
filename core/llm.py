from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import APP_CONFIG

def get_gemini_model(purpose: str = "planner", temperature: float = 0.2):
    """
    Returns an instance of the Gemini model based on the purpose defined in config.json.
    Purposes: 'planner', 'synthesizer', 'domain_detector'
    """
    # Map domain_detector to planner model by default if not specified
    model_key = purpose if purpose in APP_CONFIG.get("models", {}) else "planner"
    model_name = APP_CONFIG.get("models", {}).get(model_key, "gemini-2.5-flash")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=2
    )
