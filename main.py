import os
import gradio as gr
from dotenv import load_dotenv
import asyncio

# Import the new deep research logic
from research_agent import deep_research, ResearchReport

# Load environment variables
load_dotenv()

async def interact(user_message, history):
    """
    Handle user interaction for Deep Research.
    """
    if not user_message:
        yield history, ""
        return

    # Append user message to Gradio history
    history = history or []
    history.append({"role": "user", "content": user_message})
    
    # Yield initial state
    yield history, ""

    # Call the deep_research generator
    # It yields status strings (progress updates) and finally a ResearchReport object
    async for update in deep_research(user_message):
        if isinstance(update, str):
            # It's a status update
            # We can show this as a temporary system message or just log it
            # For a chat interface, we can append a system message that updates
            if history[-1]["role"] != "assistant":
                history.append({"role": "assistant", "content": update})
            else:
                history[-1]["content"] = update
            yield history, ""
            
        elif isinstance(update, ResearchReport):
            # Final report
            report_md = f"# Research Report: {user_message}\n\n"
            report_md += f"## Executive Summary\n{update.executive_summary}\n\n"
            
            for section in update.sections:
                report_md += f"### {section.title}\n{section.content}\n\n"
                if section.sources:
                    report_md += "**Sources:**\n" + "\n".join([f"- {s}" for s in section.sources]) + "\n\n"
            
            report_md += f"## Risks & Uncertainties\n{update.risks_uncertainties}\n\n"
            report_md += "## What to Watch Next\n" + "\n".join([f"- {item}" for item in update.what_to_watch_next])
            
            # Replace the last status message with the final report
            history[-1]["content"] = report_md
            yield history, ""

# Create the Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("# Pydantic AI Deep Research Agent")
    gr.Markdown("Enter a stock ticker (e.g., NVDA) or a research topic to generate a detailed report.")
    
    chatbot = gr.Chatbot(label="Agent", height=700)
    msg = gr.Textbox(placeholder="Enter ticker or topic...", label="Research Query")
    
    # Submit handler
    msg.submit(
        interact,
        inputs=[msg, chatbot],
        outputs=[chatbot, msg]
    )

if __name__ == "__main__":
    demo.launch()
