#!/usr/bin/env python3
"""
ADK Master Example - Runner Script
===================================

Simple runner for the ADK Master Example agent.

Usage:
    # Interactive chat mode
    python run.py
    
    # Or use ADK CLI
    adk run agent:app
    
    # Or with ADK web interface
    adk web agent:app

Prerequisites:
    1. Install dependencies: pip install -r requirements.txt
    2. Authenticate: gcloud auth application-default login
    3. Set project: gcloud config set project YOUR_PROJECT_ID
"""

import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point."""
    from agent import interactive_chat
    
    print("""
    ==============================================================
    |         ADK MASTER EXAMPLE - All Features Demo             |
    ==============================================================
    
    This example demonstrates ALL ADK concepts in one place:
    
    LEVEL 1 - Foundations:
      - Basic Agent structure
      - LlmAgent with configuration
      - Prompt engineering patterns
    
    LEVEL 2 - Multi-Agent:
      - sub_agents for delegation
      - AgentTool for agent-as-tool
    
    LEVEL 3 - Workflows:
      - SequentialAgent (pipeline)
      - ParallelAgent (concurrent)
      - LoopAgent (iteration)
      - Custom BaseAgent (validation)
    
    LEVEL 4 - Tools:
      - FunctionTool with ToolContext
      - google_search (built-in)
      - State-aware tools
    
    LEVEL 5 - Callbacks:
      - before_agent_callback
      - after_agent_callback
      - before_tool_callback
      - after_tool_callback
      - before_model_callback
    
    LEVEL 6 - State Management:
      - output_key for state flow
      - Session state persistence
      - Template variables {{key}}
    
    LEVEL 8 - Production:
      - Dataclass configuration
      - Rate limiting
      - Structured output (Pydantic)
    
    ==============================================================
    """)
    
    asyncio.run(interactive_chat())


def run_adk_web():
    """Run with ADK web interface."""
    import subprocess
    subprocess.run(["adk", "web", "agent:app"], cwd=os.path.dirname(__file__))


def run_adk_cli():
    """Run with ADK CLI."""
    import subprocess
    subprocess.run(["adk", "run", "agent:app"], cwd=os.path.dirname(__file__))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "web":
            run_adk_web()
        elif sys.argv[1] == "cli":
            run_adk_cli()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python run.py [web|cli]")
    else:
        main()
