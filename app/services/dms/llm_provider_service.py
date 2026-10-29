import os
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def generate_document_summary(
    document_text: str,
    document_title: str = "Document",
    summary_type: str = "detailed",
    custom_instructions: Optional[str] = None
) -> str:
    """
    Generates a structured summary of document text.
    Uses configured LLM API (OpenAI, Gemini, Groq) if available,
    otherwise falls back to an extractive markdown summary.
    """
    clean_text = (document_text or "").strip()
    if not clean_text or clean_text.startswith("[Binary file") or clean_text.startswith("[Unsupported file"):
        return f"Navi System Notification: Document '{document_title}' has no readable text content to summarize."

    # Check for external LLM API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if openai_key:
        try:
            import urllib.request
            import json

            prompt = (
                f"You are Navi, an intelligent enterprise document assistant. "
                f"Summarize the following document titled '{document_title}'.\n"
                f"Summary format style: {summary_type}.\n"
            )
            if custom_instructions:
                prompt += f"Special instructions: {custom_instructions}\n"
            prompt += f"\n--- Document Content ---\n{clean_text[:6000]}"

            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI summary call failed, falling back to extractive summary: {e}")

    # Built-in extractive summary generator
    paragraphs = [p.strip() for p in clean_text.split("\n") if len(p.strip()) > 30]
    total_words = len(clean_text.split())

    if summary_type == "brief":
        key_points = paragraphs[:2]
        return f"**Quick Overview of {document_title}**\n\n" + "\n\n".join(key_points)
    elif summary_type == "key_points":
        bullet_points = [f"- {p[:180]}..." if len(p) > 180 else f"- {p}" for p in paragraphs[:5]]
        return f"### Key Highlights: {document_title}\n\n" + "\n".join(bullet_points)
    elif summary_type == "executive":
        exec_intro = paragraphs[0] if paragraphs else "No detailed text available."
        highlights = "\n".join([f"- {p[:150]}..." for p in paragraphs[1:4]])
        return (
            f"## Executive Summary: {document_title}\n\n"
            f"**Core Subject:** {exec_intro}\n\n"
            f"### High-Level Takeaways:\n{highlights}\n\n"
            f"*Document Scope: ~{total_words} words.*"
        )
    else:  # detailed
        main_body = "\n\n".join(paragraphs[:6]) if paragraphs else clean_text[:800]
        return (
            f"### Comprehensive Summary of {document_title}\n\n"
            f"{main_body}\n\n"
            f"---\n"
            f"*Metrics: Approximately {total_words} words analyzed across document content.*"
        )


def generate_grounded_answer(
    question: str,
    context_chunks: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Generates a grounded answer with document citations.
    """
    citations = []
    for c in context_chunks[:4]:
        citations.append({
            "document_id": c.get("document_id"),
            "document_title": c.get("document_title") or f"Document #{c.get('document_id')}",
            "document_number": c.get("document_number"),
            "page_number": c.get("page_number", 1),
            "snippet": c.get("text", "")[:180].strip()
        })

    if not context_chunks:
        return {
            "answer": (
                "I couldn't find any documents matching your question in your accessible folders. "
                "Please ensure the relevant documents are uploaded and that you have permission to view them."
            ),
            "citations": [],
            "model": "navi-ai",
            "tokens_used": 0
        }

    # Check for OpenAI or external LLM API
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import urllib.request
            import json

            context_str = "\n\n".join([
                f"[Doc {c.get('document_title')} (Page {c.get('page_number', 1)})]: {c.get('text', '')}"
                for c in context_chunks[:4]
            ])

            system_prompt = (
                "You are Navi, an intelligent DMS assistant. Answer the user's question strictly "
                "using the provided document excerpts. Cite document names and page numbers where relevant."
            )

            messages = [{"role": "system", "content": system_prompt}]
            if conversation_history:
                for msg in conversation_history[-4:]:
                    messages.append({
                        "role": "user" if msg.get("sender") == "user" else "assistant",
                        "content": msg.get("content", "")
                    })

            messages.append({
                "role": "user",
                "content": f"Context excerpts:\n{context_str}\n\nQuestion: {question}"
            })

            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.2
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                ans = res_data["choices"][0]["message"]["content"]
                tokens = res_data.get("usage", {}).get("total_tokens", 0)
                return {
                    "answer": ans,
                    "citations": citations,
                    "model": "gpt-4o-mini",
                    "tokens_used": tokens
                }
        except Exception as e:
            logger.warning(f"OpenAI grounded answer call failed, using fallback synthesizer: {e}")

    # Fallback synthesizer using context chunks
    top_chunk = context_chunks[0]
    top_title = top_chunk.get("document_title") or f"Document #{top_chunk.get('document_id')}"
    page = top_chunk.get("page_number", 1)
    snippet = top_chunk.get("text", "")[:300].strip()

    answer = (
        f"Based on **{top_title}** (Page {page}):\n\n"
        f"> \"{snippet}...\"\n\n"
        f"You can review the complete document referenced below for additional details."
    )

    return {
        "answer": answer,
        "citations": citations,
        "model": "navi-ai",
        "tokens_used": len(snippet.split())
    }
