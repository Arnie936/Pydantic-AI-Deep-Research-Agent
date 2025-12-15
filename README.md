# Pydantic AI Deep Research Agent

This project implements a sophisticated **Deep Research Agent** using [Pydantic AI](https://github.com/pydantic/pydantic-ai), Gradio, and OpenAI's latest models.

Unlike simple chatbots, this agent functions as an autonomous research team. It orchestrates multiple specialized AI agents to plan, research, and synthesize detailed reports on any stock ticker or general topic.

## Key Features

- **ðŸ§  Multi-Agent Orchestration**: Coordination between four specialized agents (Classifier, Planner, Researcher, Writer).
- **ðŸŒ Real-Time Web Research**: Integrated with **DuckDuckGo** for live search results.
- **ðŸ“„ Content Scraping**: Fetches and reads actual web page content (not just snippets) for deep analysis.
- **âš¡ Parallel Execution**: Runs research on multiple angles simultaneously for speed.
- **ðŸ“Š Structured Reporting**: Generates a professional Markdown report with:
  - Executive Summary
  - Detailed Sections with Citations
  - Risks & Uncertainties
  - "What to Watch Next"

## Architecture

The system follows a multi-step workflow defined in `research_agent.py`:

1.  **Classify**: Determines if the input is a Stock Ticker (e.g., "NVDA") or a General Topic.
2.  **Initial Discovery**: Performs a quick search to understand the context.
3.  **Plan**: Generates 3-4 distinct research angles (e.g., "SWOT Analysis", "Financial Performance", "Competitor Landscape").
4.  **Deep Dive (Parallel)**:
    - Spins up a `research_worker_agent` for *each* angle.
    - Agents independently search, scrape, and summarize findings.
5.  **Synthesize**: The `writer_agent` compiles all section findings into a final cohesive report.

## Prerequisites

- Python 3.9+
- OpenAI API Key (Access to `gpt-4o` or `gpt-5-mini` `gpt-5.2` recommended)

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd <project-folder>
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    - Create a `.env` file in the root directory.
    - Add your OpenAI API key:
      ```env
      OPENAI_API_KEY=sk-...
      ```

## Usage

Run the Gradio application:

```bash
python main.py
```

Open your browser to the local URL provided (usually `http://127.0.0.1:7860`).

### Example Queries
- **Stock**: `NVDA`, `TSLA`, `AAPL`
- **Topic**: `The future of Solid State Batteries`, `Impact of AI on Healthcare`

## Project Structure

- `main.py`: The Gradio frontend and UI logic.
- `research_agent.py`: Core logic containing the agent definitions, tools, and the `deep_research` orchestration generator.
- `requirements.txt`: Python package dependencies.
