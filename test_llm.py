import os
from dotenv import load_dotenv
from src.tools.llm_tools import get_llm

load_dotenv()
os.environ["LLM_PROVIDER"] = "openrouter"

def test_llm():
    print("Testing LLM connectivity with reduced tokens (500)...")
    try:
        llm = get_llm(max_tokens=500)
        res = llm.invoke("Hello, respond with ONLY the word 'READY' if you can hear me.")
        print(f"Response: {res.content}")
    except Exception as e:
        print(f"LLM Error: {e}")

if __name__ == "__main__":
    test_llm()
