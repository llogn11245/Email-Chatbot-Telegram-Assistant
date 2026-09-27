from backend.agent.retriever import get_features, get_retriever


def build_agent(model, system_prompt: str):
    """Ráp agent. Giữ seam để sau này chèn node retrieval vào LangGraph."""
    from langgraph.prebuilt import create_react_agent

    from backend.agent.tools import get_tools

    return create_react_agent(model, get_tools(get_features({})), prompt=system_prompt)


def build_context_messages(settings: dict, user_text: str) -> list:
    """Trả về các message ngữ cảnh (RAG) chèn trước câu hỏi của user."""
    retriever = get_retriever(settings)
    features = get_features(settings)
    top_k = int(features.get("top_k") or 5)
    docs = retriever.retrieve(user_text, top_k=top_k)
    if not docs:
        return []
    context = "\n\n".join(doc.content for doc in docs)
    return [("system", f"Ngữ cảnh tham khảo:\n{context}")]
