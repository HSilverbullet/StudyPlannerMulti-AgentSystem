from langchain_openai import ChatOpenAI
from .config import OPENAI_API_KEY, OPENAI_BASE_URL

llm1 = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

