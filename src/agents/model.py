from langchain_openai import ChatOpenAI
import os


def llm_config() -> dict:
    """Provider-agnostic LLM configuration from environment variables.

    Supports any OpenAI-compatible provider (DashScope/Qwen, DeepSeek, OpenAI, ...):
      LLM_MODEL     - model name (e.g., qwen3.5-plus, deepseek-flash)
      LLM_API_KEY   - API key (falls back to DASHSCOPE_API_KEY)
      LLM_BASE_URL  - endpoint (falls back to DASHSCOPE_BASE_URL)
    """
    return {
        "model": os.getenv("LLM_MODEL", "qwen3.5-plus"),
        "api_key": os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY"),
        "base_url": os.getenv("LLM_BASE_URL")
        or os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    }


_cfg = llm_config()
llm = ChatOpenAI(
    model=_cfg["model"],
    temperature=0.0,
    api_key=_cfg["api_key"],
    base_url=_cfg["base_url"],
    timeout=int(os.getenv("LLM_TIMEOUT_SECONDS", "300")),
)

def extract_text(response) -> str:
    if isinstance(response.content, list) and len(response.content) > 0:
        text = response.content[0].get('text', '')
    elif hasattr(response.content, 'text'):
        text = response.content.text
    elif isinstance(response.content, str):
        text = response.content
    else:
        print("❌ WARNING: Unrecognized response content format: ", type(response.content), f"\n{response.content}")
        text = str(response.content)
    return text

llm.__dict__['extract_text'] = extract_text

__all__ = ["llm", "llm_config"]

if __name__ == "__main__":
    print(llm.invoke(input="Hello, what's your name?"))