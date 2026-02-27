import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def get_llm(temperature=0.1, max_tokens=2000):
    """
    Factory to initialize the appropriate LLM based on environment configuration.
    Supports Google Gemini (native) and OpenRouter (OpenAI-compatible).
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
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
            model="gemini-2.0-flash", 
            google_api_key=api_key,
            temperature=temperature
        )
