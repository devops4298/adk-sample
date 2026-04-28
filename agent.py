"""
ADK Master Example - Comprehensive Agent Demonstrating ALL ADK Features
========================================================================

This single file demonstrates every major ADK concept:
1. Basic Agent & LlmAgent
2. Multi-Agent Orchestration (sub_agents, AgentTool)
3. Workflow Patterns (SequentialAgent, ParallelAgent, LoopAgent)
4. Custom Tools with ToolContext
5. All Callback Types (before_agent, after_agent, before_tool, after_tool, before_model)
6. State Management (output_key, session state, template variables)
7. Custom BaseAgent for validation/control flow
8. Structured Output with Pydantic
9. Configuration Patterns
10. Memory Patterns (session state persistence)

Run with: python run.py
Requires: Google ADC authentication (gcloud auth application-default login)
"""

import os
import time
import json
import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator, Optional
from datetime import datetime

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# === ADK Core Imports ===
from google.adk.agents import Agent, LlmAgent
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext, FunctionTool, google_search, AgentTool
from google.adk.events import Event, EventActions
from google.adk.apps.app import App
from google.genai import types

# Load environment variables
load_dotenv(override=True)


# =============================================================================
# SECTION 1: CONFIGURATION (Level 8 - Production Pattern)
# =============================================================================

@dataclass
class AgentConfig:
    """Centralized configuration - demonstrates dataclass config pattern."""
    
    # Model settings
    main_model: str = "gemini-2.0-flash"
    worker_model: str = "gemini-2.0-flash"
    temperature: float = 0.7
    
    # Workflow settings
    max_loop_iterations: int = 3
    max_retries: int = 2
    
    # Rate limiting
    requests_per_minute: int = 30
    
    # Feature flags
    enable_rate_limiting: bool = True
    debug_mode: bool = True


config = AgentConfig()


# =============================================================================
# SECTION 2: PYDANTIC MODELS FOR STRUCTURED OUTPUT (Level 1 & 8)
# =============================================================================

class ResearchFinding(BaseModel):
    """Single research finding with structured data."""
    topic: str = Field(description="The topic researched")
    summary: str = Field(description="Brief summary of findings")
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)
    sources: list[str] = Field(default_factory=list, description="Source references")


class ResearchReport(BaseModel):
    """Complete research report - demonstrates structured output."""
    title: str = Field(description="Report title")
    findings: list[ResearchFinding] = Field(description="List of findings")
    conclusion: str = Field(description="Overall conclusion")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskPlan(BaseModel):
    """Task planning output - used by planner agent."""
    task_name: str
    steps: list[str]
    estimated_complexity: str  # "simple", "moderate", "complex"


# =============================================================================
# SECTION 3: CUSTOM TOOLS WITH TOOL CONTEXT (Level 4)
# =============================================================================

def get_current_time(tool_context: ToolContext) -> str:
    """
    Simple tool demonstrating ToolContext for state access.
    
    This tool:
    - Reads from session state
    - Writes to session state
    - Returns formatted response
    """
    # Read from state (if exists)
    timezone = tool_context.state.get("user_timezone", "UTC")
    call_count = tool_context.state.get("time_tool_calls", 0)
    
    # Update state
    tool_context.state["time_tool_calls"] = call_count + 1
    tool_context.state["last_time_check"] = datetime.now().isoformat()
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return f"Current time ({timezone}): {current_time} | This tool has been called {call_count + 1} times this session."


def calculate_expression(expression: str, tool_context: ToolContext) -> str:
    """
    Calculator tool with input validation and state tracking.
    
    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2 * 3")
        tool_context: ADK tool context for state access
    
    Returns:
        Calculation result or error message
    """
    # Track calculations in state
    calculations = tool_context.state.get("calculation_history", [])
    
    # Security: Only allow safe characters
    allowed_chars = set("0123456789+-*/().% ")
    if not all(c in allowed_chars for c in expression):
        return "Error: Expression contains invalid characters. Only numbers and +-*/().% allowed."
    
    try:
        # Safe evaluation
        result = eval(expression, {"__builtins__": {}}, {})
        
        # Store in history
        calculations.append({
            "expression": expression,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        tool_context.state["calculation_history"] = calculations[-10:]  # Keep last 10
        
        return f"Result: {expression} = {result}"
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"


def store_note(title: str, content: str, tool_context: ToolContext) -> str:
    """
    Note storage tool demonstrating persistent state.
    
    Args:
        title: Note title
        content: Note content
        tool_context: ADK tool context
    
    Returns:
        Confirmation message
    """
    notes = tool_context.state.get("user_notes", {})
    notes[title] = {
        "content": content,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    tool_context.state["user_notes"] = notes
    
    return f"Note '{title}' saved successfully. You now have {len(notes)} notes stored."


def retrieve_notes(tool_context: ToolContext) -> str:
    """
    Retrieve all stored notes.
    
    Args:
        tool_context: ADK tool context
    
    Returns:
        Formatted list of notes or message if empty
    """
    notes = tool_context.state.get("user_notes", {})
    
    if not notes:
        return "No notes stored yet. Use store_note to save notes."
    
    result = "=== Your Notes ===\n"
    for title, data in notes.items():
        result += f"\n* {title}\n"
        result += f"   Content: {data['content']}\n"
        result += f"   Created: {data['created_at']}\n"
    
    return result


def get_session_summary(tool_context: ToolContext) -> str:
    """
    Get summary of current session state - useful for debugging.
    
    Args:
        tool_context: ADK tool context
    
    Returns:
        Session state summary
    """
    state = dict(tool_context.state)
    
    summary = "=== Session State Summary ===\n"
    summary += f"Total state keys: {len(state)}\n\n"
    
    for key, value in state.items():
        if isinstance(value, (dict, list)):
            summary += f"• {key}: {type(value).__name__} with {len(value)} items\n"
        else:
            summary += f"• {key}: {value}\n"
    
    return summary


# =============================================================================
# SECTION 4: CALLBACKS (Level 5 - All Callback Types)
# =============================================================================

# --- Before Agent Callback ---
async def before_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    """
    Called BEFORE agent processes user input.
    
    Use cases:
    - Input validation
    - State initialization
    - Prerequisite checks
    
    Returns:
    - None: Continue to agent
    - Content: Short-circuit with this response (agent won't run)
    """
    if config.debug_mode:
        print(f"\n>> [BEFORE_AGENT] Agent starting...")
    
    # Initialize session state if needed
    if "session_start" not in callback_context.state:
        callback_context.state["session_start"] = datetime.now().isoformat()
        callback_context.state["message_count"] = 0
        callback_context.state["user_timezone"] = "UTC"
    
    # Increment message counter
    callback_context.state["message_count"] = callback_context.state.get("message_count", 0) + 1
    
    # Example: Block certain inputs (uncomment to test)
    # user_text = callback_context.user_content.parts[0].text.lower()
    # if "forbidden" in user_text:
    #     return types.Content(parts=[types.Part(text="I cannot process that request.")])
    
    return None  # Continue to agent


# --- After Agent Callback ---
async def after_agent_callback(callback_context: CallbackContext) -> types.Content | None:
    """
    Called AFTER agent generates response.
    
    Use cases:
    - Response validation
    - Logging/auditing
    - Memory storage
    - Response transformation
    
    Returns:
    - None: Pass through original response
    - Content: Replace response with this
    """
    if config.debug_mode:
        print(f"<< [AFTER_AGENT] Agent completed. Messages this session: {callback_context.state.get('message_count', 0)}")
    
    # Update last activity
    callback_context.state["last_activity"] = datetime.now().isoformat()
    
    # Example: Add footer to response (uncomment to test)
    # response_text = callback_context.agent_response.parts[0].text
    # return types.Content(parts=[types.Part(text=f"{response_text}\n\n---\n_Session messages: {callback_context.state.get('message_count', 0)}_")])
    
    return None  # Pass through original


# --- Before Tool Callback ---
def before_tool_callback(
    tool, 
    args: dict, 
    tool_context: ToolContext
) -> dict | None:
    """
    Called BEFORE each tool executes.
    
    Use cases:
    - Tool access control
    - Argument validation
    - Auto-approval for certain conditions
    - Rate limiting per tool
    
    Args:
        tool: The tool about to execute
        args: Arguments passed to the tool
        tool_context: Tool context for state access
    
    Returns:
    - None: Continue with tool execution
    - dict: Skip tool, return this as result
    """
    if config.debug_mode:
        print(f"  [TOOL>>] {tool.name}, Args: {args}")
    
    # Track tool usage
    tool_usage = tool_context.state.get("tool_usage", {})
    tool_usage[tool.name] = tool_usage.get(tool.name, 0) + 1
    tool_context.state["tool_usage"] = tool_usage
    
    # Example: Block specific tool (uncomment to test)
    # if tool.name == "calculate_expression" and "dangerous" in str(args):
    #     return {"error": "Operation blocked by security policy"}
    
    return None  # Continue with tool


# --- After Tool Callback ---
def after_tool_callback(
    tool,
    args: dict,
    tool_context: ToolContext,
    tool_response: dict
) -> dict | None:
    """
    Called AFTER each tool executes.
    
    Use cases:
    - Log tool results
    - Transform tool output
    - Trigger side effects
    - Update analytics
    
    Returns:
    - None: Pass through original response
    - dict: Replace tool response with this
    """
    if config.debug_mode:
        response_preview = str(tool_response)[:100] + "..." if len(str(tool_response)) > 100 else str(tool_response)
        print(f"  [TOOL<<] {tool.name} completed. Response: {response_preview}")
    
    # Track successful tool calls
    successful_tools = tool_context.state.get("successful_tool_calls", [])
    successful_tools.append({
        "tool": tool.name,
        "timestamp": datetime.now().isoformat()
    })
    tool_context.state["successful_tool_calls"] = successful_tools[-20:]  # Keep last 20
    
    return None  # Pass through original


# --- Before Model Callback ---
def before_model_callback(callback_context: CallbackContext, llm_request) -> None:
    """
    Called BEFORE each LLM API call.
    
    Use cases:
    - Rate limiting
    - Request logging
    - Token counting
    - Request modification
    
    Note: Returns None (void) - cannot short-circuit LLM call
    """
    if config.debug_mode:
        print(f"  [LLM>>] Call initiated...")
    
    # Simple rate limiting
    if config.enable_rate_limiting:
        state = callback_context.state
        
        current_time = time.time()
        window_start = state.get("rate_limit_window_start", current_time)
        request_count = state.get("rate_limit_count", 0)
        
        # Reset window if minute passed
        if current_time - window_start >= 60:
            state["rate_limit_window_start"] = current_time
            state["rate_limit_count"] = 1
        else:
            state["rate_limit_count"] = request_count + 1
            
            # Throttle if over limit
            if request_count >= config.requests_per_minute:
                sleep_time = 60 - (current_time - window_start)
                if sleep_time > 0:
                    print(f"  [WAIT] Rate limit reached. Sleeping {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    state["rate_limit_window_start"] = time.time()
                    state["rate_limit_count"] = 1


# =============================================================================
# SECTION 5: CUSTOM BASE AGENT FOR VALIDATION (Level 3 - Loop Control)
# =============================================================================

class ValidationCheckerAgent(BaseAgent):
    """
    Custom agent that checks if a condition is met and escalates to exit loop.
    
    This demonstrates:
    - Extending BaseAgent
    - Implementing _run_async_impl
    - Using EventActions for loop control
    - Reading from session state
    """
    
    # Declare Pydantic fields
    state_key: str = ""
    required_value: Optional[str] = None
    
    def __init__(self, name: str, state_key: str, required_value: Optional[str] = None, **kwargs):
        """
        Args:
            name: Agent name
            state_key: Key to check in session state
            required_value: If provided, state[key] must equal this value
        """
        super().__init__(name=name, state_key=state_key, required_value=required_value, **kwargs)
    
    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Check validation condition and escalate if met.
        """
        state_value = context.session.state.get(self.state_key)
        
        if config.debug_mode:
            print(f"  [CHECK] Checking state['{self.state_key}'] = {state_value}")
        
        # Check condition
        condition_met = False
        if self.required_value is not None:
            condition_met = state_value == self.required_value
        else:
            condition_met = state_value is not None and state_value != ""
        
        if condition_met:
            # Validation passed - escalate to exit loop
            if config.debug_mode:
                print(f"  [PASS] Condition met! Escalating to exit loop.")
            yield Event(
                author=self.name,
                actions=EventActions(escalate=True),
            )
        else:
            # Validation failed - continue loop
            if config.debug_mode:
                print(f"  [FAIL] Condition not met. Continuing loop...")
            yield Event(author=self.name)


# =============================================================================
# SECTION 6: SUB-AGENTS (Level 2 - Multi-Agent Patterns)
# =============================================================================

# --- Simple Worker Agent (for AgentTool pattern) ---
researcher_agent = LlmAgent(
    name="researcher_agent",
    model=config.worker_model,
    description="Expert researcher that finds information on any topic.",
    instruction="""You are a research specialist. When asked about a topic:
1. Use google_search to find current information
2. Summarize key findings clearly
3. Always cite your sources

Be thorough but concise.""",
    tools=[google_search],
    output_key="research_output",  # Stores output in state
)


# --- Analyzer Agent (reads from state) ---
analyzer_agent = LlmAgent(
    name="analyzer_agent",
    model=config.worker_model,
    description="Analyzes information and provides insights.",
    instruction="""You are an analyst. Your job is to:
1. Review the research provided
2. Identify key patterns and insights
3. Provide actionable recommendations

Research to analyze: {{research_output}}

Provide a structured analysis with clear sections.""",
    output_key="analysis_output",
)


# --- Creative Writer Agent (high temperature) ---
creative_writer_agent = LlmAgent(
    name="creative_writer_agent",
    model=config.worker_model,
    description="Creative writer with imaginative style.",
    instruction="""You are a creative writer. Transform the given topic into 
engaging, imaginative content. Use vivid language and unexpected perspectives.

Topic/Input: {{creative_input}}

Be bold and creative!""",
    generate_content_config=types.GenerateContentConfig(temperature=0.9),
    output_key="creative_output",
)


# --- Focused Writer Agent (low temperature) ---
focused_writer_agent = LlmAgent(
    name="focused_writer_agent",
    model=config.worker_model,
    description="Focused writer with precise style.",
    instruction="""You are a technical writer. Transform the given topic into
clear, precise, well-structured content. Focus on accuracy and clarity.

Topic/Input: {{creative_input}}

Be precise and factual.""",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    output_key="focused_output",
)


# --- Critic Agent (compares outputs) ---
critic_agent = LlmAgent(
    name="critic_agent",
    model=config.worker_model,
    description="Evaluates and selects best content.",
    instruction="""You are a content critic. Compare these two versions:

CREATIVE VERSION:
{{creative_output}}

FOCUSED VERSION:
{{focused_output}}

Evaluate both and select the better one. Explain your choice briefly, 
then output the selected version as the final result.""",
    output_key="final_content",
)


# --- Planner Agent (structured output) ---
planner_agent = LlmAgent(
    name="planner_agent",
    model=config.worker_model,
    description="Creates structured task plans.",
    instruction="""You are a task planner. Given a goal, create a structured plan.

Current goal from user: {{user_goal}}

Create a clear, actionable plan.""",
    output_schema=TaskPlan,
    output_key="task_plan",
    generate_content_config=types.GenerateContentConfig(
        response_mime_type="application/json"
    ),
)


# =============================================================================
# SECTION 7: WORKFLOW AGENTS (Level 3 - Workflow Patterns)
# =============================================================================

# --- Parallel Agent: Run creative and focused writers simultaneously ---
parallel_writers = ParallelAgent(
    name="parallel_writers",
    description="Runs creative and focused writers in parallel.",
    sub_agents=[creative_writer_agent, focused_writer_agent],
)


# --- Sequential Pipeline: Research → Analyze ---
research_pipeline = SequentialAgent(
    name="research_pipeline",
    description="Research and analyze a topic.",
    sub_agents=[researcher_agent, analyzer_agent],
)


# --- Loop Agent with Validation ---
# This demonstrates retry logic until condition is met
refinement_loop = LoopAgent(
    name="refinement_loop",
    description="Iteratively refines content until quality threshold met.",
    sub_agents=[
        planner_agent,
        ValidationCheckerAgent(
            name="plan_validator",
            state_key="task_plan",
        ),
    ],
    max_iterations=config.max_loop_iterations,
)


# --- Complex Workflow: Parallel → Critique ---
content_generation_workflow = SequentialAgent(
    name="content_generation_workflow",
    description="Generate content with parallel writers then critique.",
    sub_agents=[parallel_writers, critic_agent],
)


# =============================================================================
# SECTION 8: ROOT AGENT (Combines Everything)
# =============================================================================

ROOT_INSTRUCTION = """You are the ADK Master Assistant - a comprehensive demo agent 
showcasing all Google ADK features.

## Your Capabilities:

### 1. Basic Tools:
- **get_current_time**: Get current time (demonstrates state tracking)
- **calculate_expression**: Calculate math expressions safely
- **store_note** / **retrieve_notes**: Persistent note storage
- **get_session_summary**: View current session state

### 2. Research & Analysis (AgentTool pattern):
- **research_agent**: Delegate deep research tasks using google_search
- **research_and_analyze**: Full research → analysis pipeline

### 3. Content Generation (Workflow patterns):
- **generate_content**: Parallel creative/focused writing with critique
- **plan_task**: Create structured task plans with validation loop

### 4. Session Features:
- I track your interactions across the session
- Notes and calculations are persisted
- Tool usage is monitored

## How to Use:
- Ask me to research any topic
- Request calculations or time checks
- Store and retrieve notes
- Ask for content on any subject
- Request a task plan for any goal
- Ask for a session summary to see state

Current date: {current_date}
Session started: {{session_start}}
Messages this session: {{message_count}}
"""


# Create root agent with all features
root_agent = Agent(
    name="adk_master_agent",
    model=config.main_model,
    description="Comprehensive ADK demo agent with all features.",
    instruction=ROOT_INSTRUCTION.format(current_date=datetime.now().strftime("%Y-%m-%d")),
    
    # === Tools (Level 4) ===
    tools=[
        # Basic function tools
        FunctionTool(get_current_time),
        FunctionTool(calculate_expression),
        FunctionTool(store_note),
        FunctionTool(retrieve_notes),
        FunctionTool(get_session_summary),
        
        # AgentTool - wrap agents as tools (Level 2)
        AgentTool(agent=researcher_agent),
        AgentTool(agent=research_pipeline),
        AgentTool(agent=content_generation_workflow),
        AgentTool(agent=refinement_loop),
    ],
    
    # === Callbacks (Level 5) ===
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    before_model_callback=before_model_callback,
    
    # === Sub-agents for delegation (Level 2) ===
    # Uncomment to enable direct agent transfer instead of AgentTool
    # sub_agents=[researcher_agent, planner_agent],
)


# =============================================================================
# SECTION 9: APP WRAPPER (Deployment)
# =============================================================================

app = App(
    name="adk_master_example",
    root_agent=root_agent,
)


# =============================================================================
# SECTION 10: DIRECT RUNNER (For Testing)
# =============================================================================

async def run_agent_turn(user_input: str, session_id: str = "default_session"):
    """
    Run a single turn with the agent.
    
    This demonstrates how to programmatically interact with the agent.
    """
    from google.adk.runners import InMemoryRunner
    
    runner = InMemoryRunner(agent=root_agent)
    
    user_content = types.Content(
        parts=[types.Part(text=user_input)],
        role="user"
    )
    
    response_parts = []
    
    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session_id,
        new_message=user_content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    response_parts.append(part.text)
    
    return "\n".join(response_parts)


# =============================================================================
# MAIN - Interactive Chat Mode
# =============================================================================

async def interactive_chat():
    """
    Interactive chat loop for testing the agent.
    """
    from google.adk.runners import InMemoryRunner
    
    print("\n" + "="*60)
    print("[ADK] MASTER EXAMPLE - Interactive Chat")
    print("="*60)
    print("\nThis agent demonstrates ALL ADK features:")
    print("- Tools with ToolContext")
    print("- All 5 callback types")
    print("- AgentTool pattern")
    print("- Sequential, Parallel, Loop workflows")
    print("- Custom BaseAgent")
    print("- Structured output (Pydantic)")
    print("- State management")
    print("\nCommands:")
    print("  'quit' or 'exit' - Exit chat")
    print("  'state' - Show session state")
    print("  'help' - Show capabilities")
    print("\n" + "-"*60 + "\n")
    
    runner = InMemoryRunner(agent=root_agent)
    session_id = f"session_{int(time.time())}"
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == 'state':
                user_input = "Use the get_session_summary tool to show me the current session state."
            
            if user_input.lower() == 'help':
                user_input = "What are all your capabilities? List them with examples."
            
            # Send to agent
            user_content = types.Content(
                parts=[types.Part(text=user_input)],
                role="user"
            )
            
            print("\nAssistant: ", end="", flush=True)
            
            response_text = ""
            async for event in runner.run_async(
                user_id="interactive_user",
                session_id=session_id,
                new_message=user_content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
            
            print(response_text)
            print()
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            if config.debug_mode:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    print("\n>> Starting ADK Master Example...")
    print("Make sure you have authenticated: gcloud auth application-default login\n")
    asyncio.run(interactive_chat())
