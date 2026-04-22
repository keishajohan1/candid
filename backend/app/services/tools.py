from langchain_core.tools import tool
from app.services.knowledge_base import get_rag_retriever

@tool
def search_verified_knowledge(query: str) -> str:
    """
    Search the internal verified knowledge base for facts about a specific topic.
    Use this tool when you need statistical data, dates, or specific claims regarding a topic.
    """
    retriever = get_rag_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "No verified facts found for the given query."
    
    formatted = "\n".join([f"- {doc.page_content}" for doc in docs])
    return f"Verified Facts Found:\n{formatted}"
