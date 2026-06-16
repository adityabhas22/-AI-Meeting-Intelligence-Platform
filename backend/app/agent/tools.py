"""The agent's one tool: search the meeting archive. Dependencies (DB session, query
embedder) travel in the run context, not as model-visible arguments. The tool records
the chunks it retrieved on the context so the API can return them as citations."""

from dataclasses import dataclass, field

from agents import RunContextWrapper, function_tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.retriever import Embedder, RetrievedChunk, hybrid_search


@dataclass
class Deps:
    session: AsyncSession
    embed: Embedder | None = None
    sources: list[RetrievedChunk] = field(default_factory=list)


def format_chunks(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant passages found in the archive."
    blocks = [
        f"[Meeting: {c.meeting_title} | {c.start_sec:.0f}-{c.end_sec:.0f}s]\n{c.text}"
        for c in chunks
    ]
    return "\n\n".join(blocks)


async def archive_search(deps: Deps, query: str) -> str:
    """Plain implementation, tested directly without the LLM in the loop."""
    chunks = await hybrid_search(deps.session, query, embed=deps.embed)
    deps.sources.extend(chunks)
    return format_chunks(chunks)


@function_tool
async def search_archive(ctx: RunContextWrapper[Deps], query: str) -> str:
    """Search the meeting transcript archive for passages relevant to the query.

    Args:
        query: A natural-language description of what to find across past meetings.
    """
    return await archive_search(ctx.context, query)
