import os
from dotenv import load_dotenv
from typing import TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from app.db import search_documents

load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile")


# ── State passed between nodes ─────────────────────────────────
class BrainState(TypedDict):
    question: str
    source_type: str        # optional filter
    days_back: int          # optional filter
    retrieved: list         # chunks found
    answer: str             # final synthesized answer
    sources: list           # which sources were used


# ── Node 1: Retrieve ──────────────────────────────────────────
def retrieve(state: BrainState) -> BrainState:
    results = search_documents(
        query=state["question"],
        limit=8,   # pull more chunks for synthesis
        source_type=state.get("source_type"),
        days_back=state.get("days_back")
    )
    return {**state, "retrieved": results}


# ── Node 2: Synthesize ────────────────────────────────────────
def synthesize(state: BrainState) -> BrainState:
    retrieved = state["retrieved"]

    if not retrieved:
        return {
            **state,
            "answer": "I couldn't find anything about that in your knowledge base. Try adding some documents first.",
            "sources": []
        }

    # Build context from all retrieved chunks
    context = ""
    for i, r in enumerate(retrieved):
        context += f"\n[Source {i+1} — {r['title']} ({r['source_type']})]\n"
        context += f"{r['content']}\n"

    # Synthesize into one answer
    response = llm.invoke([
        SystemMessage(content="""You are a personal knowledge assistant.
The user has saved documents, articles, and notes. Answer their 
question by synthesizing information across ALL the provided sources 
into one coherent response.

Rules:
- Combine information from multiple sources into a unified answer
- Do NOT just list what each source says separately
- Answer ONLY from the provided sources
- If sources disagree, note the difference
- Reference sources naturally (e.g. "According to your saved 
  Wikipedia article...")
- If the sources don't cover the question, say so honestly"""),
        HumanMessage(content=f"Question: {state['question']}\n\nSaved sources:\n{context}")
    ])

    # Track unique sources used
    unique_sources = list({r["title"] for r in retrieved})

    return {
        **state,
        "answer": response.content,
        "sources": unique_sources
    }


# ── Build the graph ───────────────────────────────────────────
def build_brain():
    graph = StateGraph(BrainState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


# ── Run function ──────────────────────────────────────────────
def ask_brain(question: str, source_type: str = None,
              days_back: int = None) -> dict:
    brain = build_brain()
    result = brain.invoke({
        "question": question,
        "source_type": source_type,
        "days_back": days_back,
        "retrieved": [],
        "answer": "",
        "sources": []
    })
    return {
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "chunks_used": len(result["retrieved"])
    }