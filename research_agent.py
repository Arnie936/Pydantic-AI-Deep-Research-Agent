from __future__ import annotations
import asyncio
from typing import List, Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from ddgs import DDGS
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# --- Data Models ---

class ResearchAngle(BaseModel):
    title: str = Field(description="Title of the research angle (e.g. 'SWOT Analysis', 'Recent Financial Performance')")
    keywords: List[str] = Field(description="List of keywords to search for this angle")
    description: str = Field(description="Short description of what to look for")

class ResearchSection(BaseModel):
    title: str
    content: str
    sources: List[str] = Field(description="List of source URLs used")

class ResearchReport(BaseModel):
    executive_summary: str
    sections: List[ResearchSection]
    risks_uncertainties: str
    what_to_watch_next: List[str]

# --- Dependencies ---

@dataclass
class ResearchDeps:
    client: httpx.AsyncClient

# --- Tools ---

async def search_tool(query: str, max_results: int = 5) -> List[dict]:
    """
    Search DuckDuckGo for the given query.
    Returns a list of dictionaries with 'title', 'href', 'body'.
    """
    print(f"Executing search for: {query}")
    results = []
    try:
        # DDGS is synchronous but fast enough for this prototype, or we could run in executor
        # Using DDGS as a context manager is recommended
        with DDGS() as ddgs:
            # text() returns an iterator
            for r in ddgs.text(query, max_results=max_results):
                results.append(r)
    except Exception as e:
        print(f"Search error: {e}")
    return results

async def fetch_page_tool(ctx: RunContext[ResearchDeps], url: str) -> str:
    """
    Fetch the content of a URL and return a simplified text representation.
    """
    print(f"Fetching URL: {url}")
    try:
        response = await ctx.deps.client.get(url, follow_redirects=True, timeout=10.0)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit content length to avoid overflowing context
        return text[:10000] 
    except Exception as e:
        return f"Error fetching {url}: {e}"

# --- Agents ---

# 1. Classification Agent

class ClassificationResult(BaseModel):
    is_ticker: bool
    subject: str = Field(description="The main subject (e.g., 'NVIDIA Corporation' or 'Quantum Computing')")
    context: str = Field(description="Industry or topic context")

classify_agent = Agent(
    'openai:gpt-5-mini-2025-08-07',
    system_prompt='You are a classifier. Determine if the user input is a specific stock ticker (like NVDA, AAPL, TSLA) or a general research query. '
                  'If it is a ticker, return the company name and industry context. '
                  'If it is a general query, clarify the main topic.',
    output_type=ClassificationResult
)

# 2. Planning Agent
plan_agent = Agent(
    'openai:gpt-5-mini-2025-08-07',
    system_prompt='You are a research planner. Given a topic and initial search context, generate 3-4 distinct research angles (keywords) to investigate. '
                  'Ensure they are non-overlapping and cover key aspects (SWOT, Financials, Competitors, etc. for stocks; Key trends, History, Pros/Cons for general topics).',
    output_type=List[ResearchAngle]
)

# 3. Research Agent (Worker)
# This agent will take a specific angle, perform searches (using tools), and summarize findings.
research_worker_agent = Agent(
    'openai:gpt-5-mini-2025-08-07',
    deps_type=ResearchDeps,
    system_prompt='You are a senior researcher. Your goal is to investigate a specific research angle deeply. '
                  '1. Use the `search_tool` to find relevant information. '
                  '2. Use the `fetch_page_tool` to read promising pages if the snippets are not enough. '
                  '3. Synthesize the findings into a concise section with citations. '
                  'Prefer primary sources for financials.',
    output_type=ResearchSection
)

@research_worker_agent.tool
async def search(ctx: RunContext[ResearchDeps], query: str) -> List[dict]:
    """Search the web for information."""
    return await search_tool(query)

@research_worker_agent.tool
async def fetch_page(ctx: RunContext[ResearchDeps], url: str) -> str:
    """Fetch and extract text from a URL."""
    return await fetch_page_tool(ctx, url)


# 4. Writer Agent
writer_agent = Agent(
    'openai:gpt-5-mini-2025-08-07',
    system_prompt='You are a professional report writer. Compile the provided research sections into a comprehensive, well-structured Markdown report. '
                  'Includes an Executive Summary, the main Sections, Risks, and What to Watch. '
                  'Ensure citations are preserved.',
    output_type=ResearchReport
)

# --- Orchestration ---

async def deep_research(user_input: str):
    """
    Main entry point for the Deep Research Agent.
    Yields status updates (strings) and finally the ResearchReport.
    """
    async with httpx.AsyncClient() as client:
        deps = ResearchDeps(client=client)
        
        # Step 1: Classify
        yield "ðŸ” Analyzing request..."
        classification_res = await classify_agent.run(
            f"Classify this input: '{user_input}'"
        )
        classification = classification_res.output
        subject = classification.subject
        context = classification.context
        
        yield f"ðŸŽ¯ Identified: {subject} ({context})"
        
        # Step 2: Initial Discovery
        yield "ðŸŒ Performing initial discovery search..."
        initial_search_results = await search_tool(f"{subject} {context} overview", max_results=3)
        initial_context = "\n".join([f"- {r['title']}: {r['body']}" for r in initial_search_results])
        
        # Step 3: Planning
        yield "ðŸ“‹ Planning research strategy..."
        plan_res = await plan_agent.run(
            f"Topic: {subject}\nContext: {context}\nInitial Search Context:\n{initial_context}"
        )
        angles = plan_res.output
        
        # Step 4: Parallel Deep Dive
        yield f"ðŸš€ Starting deep dive into {len(angles)} research angles..."
        
        async def process_angle(angle: ResearchAngle) -> ResearchSection:
            # We run the research worker for each angle
            # The worker has access to tools to search and fetch
            prompt = f"Investigate the angle: '{angle.title}'.\nDescription: {angle.description}\nKeywords: {', '.join(angle.keywords)}\nSubject: {subject}"
            result = await research_worker_agent.run(prompt, deps=deps)
            return result.output

        # Run all angles in parallel
        # We use asyncio.gather to run them concurrently
        sections = await asyncio.gather(*[process_angle(angle) for angle in angles])
        
        # Step 5: Synthesis
        yield "âœï¸ Writing final report..."
        synthesis_prompt = f"Subject: {subject}\n\n"
        for section in sections:
            synthesis_prompt += f"## {section.title}\n{section.content}\nSources: {', '.join(section.sources)}\n\n"
            
        final_report_res = await writer_agent.run(synthesis_prompt)
        report = final_report_res.output
        
        yield report

