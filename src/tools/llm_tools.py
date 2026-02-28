import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def get_llm(temperature=0.1, max_tokens=500, model_id=None):
    """
    Factory to initialize the appropriate LLM based on environment configuration.
    Supports Google Gemini (native) and OpenRouter (OpenAI-compatible).
    If model_id is provided, it overrides the default provider settings.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    # ── Specialized Model Overrides ──────────────────────────────────
    if model_id:
        if "qwen" in model_id.lower():
             return ChatOpenAI(
                model=model_id,
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
                temperature=temperature,
                max_tokens=max_tokens
            )
        # Add other specific overrides if needed
        
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-preview-09-2025:free")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        # Default to Gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model=model_id or "gemini-2.0-flash", 
            google_api_key=api_key,
            temperature=temperature
        )
