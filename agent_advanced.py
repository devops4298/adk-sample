"""
ADK Advanced Example - Production Patterns
===========================================

This file demonstrates ADVANCED production patterns:
1. Arize/Phoenix Evaluation & Observability
2. Session Storage (Firestore, BigQuery)
3. A2A (Agent-to-Agent) Protocol
4. Vertex AI Memory Bank
5. MCP (Model Context Protocol) Servers

Prerequisites:
- Google ADC authentication: gcloud auth application-default login
- Arize account (for evaluation): Set ARIZE_SPACE_ID, ARIZE_API_KEY
- Firestore enabled (for state persistence)

Run with: python agent_advanced.py
"""

import os
import json
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from dotenv import load_dotenv

# === ADK Core Imports ===
from google.adk.agents import Agent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext, FunctionTool, google_search
from google.adk.apps.app import App
from google.genai import types

load_dotenv(override=True)


# =============================================================================
# SECTION 1: CONFIGURATION
# =============================================================================

@dataclass
class AdvancedConfig:
    """Configuration for advanced features."""
    
    # Models
    model: str = "gemini-2.5-pro"
    
    # Arize (optional)
    arize_space_id: str = os.getenv("ARIZE_SPACE_ID", "")
    arize_api_key: str = os.getenv("ARIZE_API_KEY", "")
    arize_project_name: str = os.getenv("ARIZE_PROJECT_NAME", "adk-advanced-example")
    
    # Firestore (optional)
    firestore_database: str = os.getenv("FIRESTORE_DATABASE", "(default)")
    enable_firestore: bool = os.getenv("ENABLE_FIRESTORE", "false").lower() == "true"
    
    # Memory Bank (optional)
    enable_memory_bank: bool = os.getenv("ENABLE_MEMORY_BANK", "false").lower() == "true"
    
    # MCP Server (optional)
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "")
    
    # A2A (optional)
    a2a_port: int = int(os.getenv("A2A_PORT", "10000"))
    
    # Debug
    debug_mode: bool = os.getenv("DEBUG_MODE", "true").lower() == "true"


config = AdvancedConfig()


# =============================================================================
# SECTION 2: ARIZE/PHOENIX OBSERVABILITY (Level 9)
# =============================================================================

def instrument_adk_with_arize():
    """
    Instrument ADK with Arize Phoenix for observability.
    
    This enables:
    - Distributed tracing of agent calls
    - LLM call logging
    - Tool execution tracking
    - Session-based trace grouping
    
    Requires:
    - pip install openinference-instrumentation-google-adk arize-otel arize
    - ARIZE_SPACE_ID and ARIZE_API_KEY environment variables
    """
    if not config.arize_space_id or not config.arize_api_key:
        if config.debug_mode:
            print("[WARN] Arize credentials not set. Skipping instrumentation.")
        return None
    
    try:
        from arize.otel import register
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        
        # Register Arize tracer provider
        tracer_provider = register(
            space_id=config.arize_space_id,
            api_key=config.arize_api_key,
            project_name=config.arize_project_name,
        )
        
        # Instrument ADK
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        
        if config.debug_mode:
            print(f"[OK] Arize instrumentation enabled for project: {config.arize_project_name}")
        
        return tracer_provider.get_tracer(__name__)
    
    except ImportError:
        print("[WARN] Arize packages not installed. Run: pip install openinference-instrumentation-google-adk arize-otel arize")
        return None
    except Exception as e:
        print(f"[WARN] Arize instrumentation failed: {e}")
        return None


# =============================================================================
# SECTION 3: FIRESTORE SESSION/STATE PERSISTENCE (Level 10)
# =============================================================================

class FirestoreStateService:
    """
    Firestore-backed state persistence for multi-step workflows.
    
    Features:
    - Process state tracking across multiple agent steps
    - Status management (not_started, in_progress, completed, error)
    - Step data persistence
    - Audit trail with timestamps
    
    Requires:
    - pip install google-cloud-firestore
    - Firestore enabled in your GCP project
    - GOOGLE_CLOUD_PROJECT environment variable
    """
    
    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_ERROR = "error"
    
    def __init__(self, collection_name: str = "agent_sessions"):
        self.collection_name = collection_name
        self.db = None
        
        if config.enable_firestore:
            try:
                from google.cloud import firestore
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
                self.db = firestore.Client(
                    project=project_id, 
                    database=config.firestore_database
                )
                if config.debug_mode:
                    print(f"[OK] Firestore connected: {project_id}/{config.firestore_database}")
            except Exception as e:
                print(f"[WARN] Firestore connection failed: {e}")
    
    def create_session(self, session_id: str, user_id: str, metadata: dict = None) -> dict:
        """Create a new session document."""
        if not self.db:
            return {"session_id": session_id, "status": "in_memory_only"}
        
        from google.cloud import firestore
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "status": self.STATUS_IN_PROGRESS,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "metadata": metadata or {},
            "steps": {},
            "messages": [],
        }
        
        self.db.collection(self.collection_name).document(session_id).set(session_data)
        return session_data
    
    def update_step(self, session_id: str, step_name: str, status: str, data: dict = None):
        """Update a step within a session."""
        if not self.db:
            return
        
        from google.cloud import firestore
        
        doc_ref = self.db.collection(self.collection_name).document(session_id)
        doc_ref.update({
            f"steps.{step_name}": {
                "status": status,
                "data": data,
                "timestamp": firestore.SERVER_TIMESTAMP,
            },
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
    
    def append_message(self, session_id: str, role: str, content: str):
        """Append a message to session history."""
        if not self.db:
            return
        
        from google.cloud import firestore
        
        doc_ref = self.db.collection(self.collection_name).document(session_id)
        doc_ref.update({
            "messages": firestore.ArrayUnion([{
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }]),
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a session."""
        if not self.db:
            return None
        
        doc = self.db.collection(self.collection_name).document(session_id).get()
        return doc.to_dict() if doc.exists else None
    
    def complete_session(self, session_id: str, final_status: str = None):
        """Mark session as completed."""
        if not self.db:
            return
        
        from google.cloud import firestore
        
        doc_ref = self.db.collection(self.collection_name).document(session_id)
        doc_ref.update({
            "status": final_status or self.STATUS_COMPLETED,
            "completed_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })


# Global state service instance
state_service = FirestoreStateService()


# =============================================================================
# SECTION 4: MEMORY BANK CONFIGURATION (Level 12)
# =============================================================================

def get_memory_bank_config():
    """
    Configure Vertex AI Memory Bank for long-term memory.
    
    Memory topics:
    - USER_PERSONAL_INFO: Names, relationships, hobbies
    - USER_PREFERENCES: Likes, dislikes, styles
    - EXPLICIT_INSTRUCTIONS: Things user asks to remember
    - KEY_CONVERSATION_DETAILS: Important milestones
    
    Requires:
    - Vertex AI Agent Engine deployment
    - memory_service_uri configuration
    """
    if not config.enable_memory_bank:
        return None
    
    try:
        from vertexai._genai.types import (
            ManagedTopicEnum,
            MemoryBankCustomizationConfig as CustomizationConfig,
            MemoryBankCustomizationConfigMemoryTopic as MemoryTopic,
            MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic as ManagedMemoryTopic,
            ReasoningEngineContextSpecMemoryBankConfig as MemoryBankConfig,
        )
        
        memory_config = MemoryBankConfig(
            customization_configs=[
                CustomizationConfig(
                    memory_topics=[
                        MemoryTopic(
                            managed_memory_topic=ManagedMemoryTopic(
                                managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO,
                            ),
                        ),
                        MemoryTopic(
                            managed_memory_topic=ManagedMemoryTopic(
                                managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES,
                            ),
                        ),
                        MemoryTopic(
                            managed_memory_topic=ManagedMemoryTopic(
                                managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS,
                            ),
                        ),
                    ],
                ),
            ],
        )
        
        if config.debug_mode:
            print("[OK] Memory Bank configuration created")
        
        return memory_config
    
    except ImportError:
        print("[WARN] Vertex AI packages not available for Memory Bank")
        return None


def get_memory_tools():
    """
    Get memory tools for the agent.
    
    Tools:
    - PreloadMemoryTool: Auto-inject memories at turn start
    - LoadMemoryTool: On-demand memory retrieval
    """
    if not config.enable_memory_bank:
        return []
    
    try:
        from google.adk.tools.preload_memory_tool import PreloadMemoryTool
        
        if config.debug_mode:
            print("[OK] Memory tools enabled (PreloadMemoryTool)")
        
        return [PreloadMemoryTool()]
    
    except ImportError:
        print("[WARN] Memory tools not available")
        return []


# =============================================================================
# SECTION 5: MCP TOOLSET INTEGRATION (Level 13)
# =============================================================================

def get_mcp_tools():
    """
    Get MCP tools from external MCP server.
    
    Connection types supported:
    - StreamableHTTPConnectionParams: HTTP/REST-based servers
    - SseConnectionParams: Server-Sent Events servers
    - StdioConnectionParams: Local subprocess servers
    
    Requires:
    - MCP server running at MCP_SERVER_URL
    - pip install google-adk (includes MCP support)
    """
    if not config.mcp_server_url:
        return []
    
    try:
        from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
        
        # Graceful MCP toolset that handles connection failures
        class SafeMCPToolset(MCPToolset):
            """MCP toolset with graceful error handling."""
            
            async def get_tools(self, *args, **kwargs):
                try:
                    tools = await super().get_tools(*args, **kwargs)
                    if config.debug_mode:
                        print(f"[OK] MCP tools loaded: {[t.name for t in tools]}")
                    return tools
                except Exception as e:
                    print(f"[WARN] MCP server unavailable: {e}")
                    return []
        
        mcp_toolset = SafeMCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=config.mcp_server_url
            )
        )
        
        if config.debug_mode:
            print(f"[OK] MCP toolset configured: {config.mcp_server_url}")
        
        return [mcp_toolset]
    
    except ImportError:
        print("[WARN] MCP tools not available")
        return []


# =============================================================================
# SECTION 6: A2A (AGENT-TO-AGENT) PROTOCOL (Level 11)
# =============================================================================

def create_a2a_app(agent: Agent):
    """
    Expose agent via A2A protocol for inter-agent communication.
    
    Features:
    - Auto-generates agent card at /.well-known/agent.json
    - Exposes A2A-compatible REST endpoints
    - Enables remote agent discovery and invocation
    
    Usage:
        a2a_app = create_a2a_app(my_agent)
        # Run with: uvicorn agent_advanced:a2a_app --port 10000
    
    Requires:
    - pip install a2a-sdk
    """
    try:
        from google.adk.a2a.utils.agent_to_a2a import to_a2a
        
        a2a_app = to_a2a(agent, port=config.a2a_port)
        
        if config.debug_mode:
            print(f"[OK] A2A app created on port {config.a2a_port}")
            print(f"   Agent card: http://localhost:{config.a2a_port}/.well-known/agent.json")
        
        return a2a_app
    
    except ImportError:
        print("[WARN] A2A SDK not available. Run: pip install a2a-sdk")
        return None


async def call_remote_a2a_agent(agent_url: str, query: str) -> dict:
    """
    Call a remote A2A agent.
    
    Args:
        agent_url: Base URL of the A2A agent (e.g., http://localhost:10000)
        query: User query to send
    
    Returns:
        Agent response dictionary
    
    Example:
        response = await call_remote_a2a_agent(
            "http://localhost:10000",
            "What is the exchange rate for USD to EUR?"
        )
    """
    try:
        import httpx
        from a2a.client import A2ACardResolver, A2AClient
        from a2a.types import SendMessageRequest, MessageSendParams
        
        async with httpx.AsyncClient(timeout=30.0) as httpx_client:
            # Resolve agent card
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=agent_url,
            )
            agent_card = await resolver.get_agent_card()
            
            # Create client
            client = A2AClient(
                httpx_client=httpx_client,
                agent_card=agent_card,
            )
            
            # Build message payload
            payload = {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": query}],
                    "messageId": uuid4().hex,
                }
            }
            
            # Send message
            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**payload)
            )
            
            response = await client.send_message(request)
            
            return {
                "success": True,
                "response": response.model_dump(),
            }
    
    except ImportError:
        return {"success": False, "error": "A2A SDK not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SECTION 7: CALLBACKS WITH PERSISTENCE (Level 5 + 10)
# =============================================================================

# Track current session for callbacks
_current_session_id: Optional[str] = None


async def before_agent_callback_with_persistence(
    callback_context: CallbackContext
) -> types.Content | None:
    """
    Before agent callback with Firestore state persistence.
    
    Features:
    - Creates/retrieves session in Firestore
    - Initializes session state
    - Logs incoming messages
    """
    global _current_session_id
    
    if config.debug_mode:
        print("\n>> [BEFORE_AGENT] Starting with persistence...")
    
    # Get or create session ID
    session_id = callback_context.state.get("session_id")
    if not session_id:
        session_id = f"session_{uuid4().hex[:8]}"
        callback_context.state["session_id"] = session_id
        
        # Create session in Firestore
        state_service.create_session(
            session_id=session_id,
            user_id=callback_context.state.get("user_id", "anonymous"),
            metadata={"started_at": datetime.now().isoformat()}
        )
    
    _current_session_id = session_id
    
    # Log incoming message
    if callback_context.user_content and callback_context.user_content.parts:
        user_text = callback_context.user_content.parts[0].text
        state_service.append_message(session_id, "user", user_text)
    
    # Initialize counters
    callback_context.state["message_count"] = callback_context.state.get("message_count", 0) + 1
    
    return None


async def after_agent_callback_with_persistence(
    callback_context: CallbackContext
) -> types.Content | None:
    """
    After agent callback with state persistence and optional memory storage.
    
    Features:
    - Logs agent response to Firestore
    - Stores session to Memory Bank (if enabled)
    - Updates session metadata
    """
    if config.debug_mode:
        print("<< [AFTER_AGENT] Completing with persistence...")
    
    session_id = callback_context.state.get("session_id")
    
    # Log agent response
    if callback_context.agent_response and callback_context.agent_response.parts:
        response_text = callback_context.agent_response.parts[0].text
        state_service.append_message(session_id, "assistant", response_text[:1000])  # Truncate
    
    # Store to Memory Bank (if enabled)
    if config.enable_memory_bank:
        try:
            await callback_context.add_session_to_memory()
            if config.debug_mode:
                print("  [MEM] Session stored to Memory Bank")
        except Exception as e:
            if config.debug_mode:
                print(f"  [WARN] Memory Bank storage failed: {e}")
    
    return None


# =============================================================================
# SECTION 8: TOOLS
# =============================================================================

def get_current_time(tool_context: ToolContext) -> str:
    """Get current time with timezone."""
    timezone = tool_context.state.get("user_timezone", "UTC")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Current time ({timezone}): {current_time}"


def store_user_preference(
    preference_type: str, 
    preference_value: str, 
    tool_context: ToolContext
) -> str:
    """
    Store a user preference (demonstrates state + persistence).
    
    Args:
        preference_type: Type of preference (e.g., "language", "theme")
        preference_value: Value to store
        tool_context: ADK tool context
    
    Returns:
        Confirmation message
    """
    # Store in session state
    preferences = tool_context.state.get("user_preferences", {})
    preferences[preference_type] = preference_value
    tool_context.state["user_preferences"] = preferences
    
    # Also persist to Firestore
    session_id = tool_context.state.get("session_id")
    if session_id:
        state_service.update_step(
            session_id=session_id,
            step_name="preferences",
            status="updated",
            data=preferences
        )
    
    return f"Preference saved: {preference_type} = {preference_value}"


def get_user_preferences(tool_context: ToolContext) -> str:
    """Retrieve all stored user preferences."""
    preferences = tool_context.state.get("user_preferences", {})
    
    if not preferences:
        return "No preferences stored yet."
    
    result = "Your preferences:\n"
    for key, value in preferences.items():
        result += f"  • {key}: {value}\n"
    
    return result


async def call_external_agent(
    agent_url: str,
    query: str,
    tool_context: ToolContext
) -> str:
    """
    Call an external A2A agent (demonstrates A2A client).
    
    Args:
        agent_url: URL of the A2A agent
        query: Query to send
        tool_context: ADK tool context
    
    Returns:
        Response from external agent
    """
    result = await call_remote_a2a_agent(agent_url, query)
    
    if result["success"]:
        return f"External agent response: {json.dumps(result['response'], indent=2)}"
    else:
        return f"Failed to call external agent: {result['error']}"


def get_session_info(tool_context: ToolContext) -> str:
    """Get information about current session and features enabled."""
    session_id = tool_context.state.get("session_id", "unknown")
    
    info = f"""
=== Session Information ===
Session ID: {session_id}
Message Count: {tool_context.state.get('message_count', 0)}

=== Features Enabled ===
- Arize Observability: {'[ON]' if config.arize_api_key else '[OFF]'}
- Firestore Persistence: {'[ON]' if config.enable_firestore else '[OFF]'}
- Memory Bank: {'[ON]' if config.enable_memory_bank else '[OFF]'}
- MCP Server: {'[ON]' if config.mcp_server_url else '[OFF]'}
- A2A Protocol: Available on port {config.a2a_port}

=== State Keys ===
{', '.join(tool_context.state.keys()) if tool_context.state else 'None'}
"""
    return info


# =============================================================================
# SECTION 9: ROOT AGENT
# =============================================================================

ADVANCED_INSTRUCTION = """You are an Advanced ADK Assistant demonstrating production patterns.

## Your Capabilities:

### Basic Tools:
- **get_current_time**: Get current time
- **store_user_preference**: Store preferences (persisted to database)
- **get_user_preferences**: Retrieve stored preferences
- **get_session_info**: View session and feature information

### Advanced Features (if enabled):
- **Arize Observability**: All calls traced to Arize Phoenix
- **Firestore Persistence**: Session and state persisted to database
- **Memory Bank**: Long-term memory across conversations
- **MCP Tools**: External tools from MCP server
- **A2A Protocol**: Can call/be called by other agents

### How to Test:
1. "What time is it?" - Basic tool
2. "Remember my favorite color is blue" - Preference storage
3. "What are my preferences?" - Preference retrieval
4. "Show session info" - Feature status
5. "Search for X" - Google search (if available)

Current Session: {{session_id}}
Messages: {{message_count}}
"""


def create_advanced_agent() -> Agent:
    """Create the advanced agent with all production features."""
    
    # Collect tools
    tools = [
        FunctionTool(get_current_time),
        FunctionTool(store_user_preference),
        FunctionTool(get_user_preferences),
        FunctionTool(get_session_info),
        google_search,
    ]
    
    # Add Memory tools if enabled
    tools.extend(get_memory_tools())
    
    # Add MCP tools if configured
    tools.extend(get_mcp_tools())
    
    # Create agent
    agent = Agent(
        name="advanced_adk_agent",
        model=config.model,
        description="Advanced ADK agent with production patterns",
        instruction=ADVANCED_INSTRUCTION,
        tools=tools,
        before_agent_callback=before_agent_callback_with_persistence,
        after_agent_callback=after_agent_callback_with_persistence,
    )
    
    return agent


# Create agent instance
root_agent = create_advanced_agent()

# Create app
app = App(
    name="adk_advanced_example",
    root_agent=root_agent,
)

# Create A2A app (for remote access)
a2a_app = create_a2a_app(root_agent)


# =============================================================================
# SECTION 10: EVALUATION HELPERS (Level 9)
# =============================================================================

def create_evaluation_templates():
    """
    Create Phoenix evaluation templates for LLM-as-judge evaluation.
    
    Returns templates for:
    - Response quality
    - Tool usage correctness
    - Task completion
    """
    try:
        from phoenix.evals import ClassificationTemplate
        
        response_quality = ClassificationTemplate(
            rails=["good", "poor"],
            template="""
Evaluate this agent response:

User Query: {query}
Agent Response: {response}
Expected Behavior: {expected}

- good: Response is accurate, helpful, and addresses the user's needs
- poor: Response is inaccurate, unhelpful, or misses the point

Classification:
""",
        )
        
        tool_usage = ClassificationTemplate(
            rails=["correct", "incorrect"],
            template="""
Evaluate tool usage:

User Query: {query}
Tools Expected: {expected_tools}
Tools Used: {actual_tools}

- correct: Appropriate tools were used correctly
- incorrect: Wrong tools or incorrect usage

Classification:
""",
        )
        
        return {
            "response_quality": response_quality,
            "tool_usage": tool_usage,
        }
    
    except ImportError:
        print("[WARN] Phoenix not installed for evaluation templates")
        return {}


# =============================================================================
# SECTION 11: INTERACTIVE RUNNER
# =============================================================================

async def interactive_chat():
    """Interactive chat loop with the advanced agent."""
    from google.adk.runners import InMemoryRunner
    
    # Initialize Arize tracing
    instrument_adk_with_arize()
    
    print("\n" + "="*70)
    print("[ADK] ADVANCED EXAMPLE - Production Patterns Demo")
    print("="*70)
    print(f"""
Features Enabled:
  - Arize Observability: {'[ON]' if config.arize_api_key else '[OFF] Set ARIZE_SPACE_ID & ARIZE_API_KEY'}
  - Firestore Persistence: {'[ON]' if config.enable_firestore else '[OFF] Set ENABLE_FIRESTORE=true'}
  - Memory Bank: {'[ON]' if config.enable_memory_bank else '[OFF] Set ENABLE_MEMORY_BANK=true'}
  - MCP Server: {'[ON] ' + config.mcp_server_url if config.mcp_server_url else '[OFF] Set MCP_SERVER_URL'}
  - A2A Protocol: [ON] Available (run: uvicorn agent_advanced:a2a_app --port {config.a2a_port})

Commands:
  'quit' - Exit
  'info' - Show session info
  'help' - Show capabilities
""")
    print("-"*70 + "\n")
    
    runner = InMemoryRunner(agent=root_agent)
    session_id = f"session_{uuid4().hex[:8]}"
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                # Complete session in Firestore
                state_service.complete_session(session_id)
                print("\nSession completed. Goodbye!")
                break
            
            if user_input.lower() == 'info':
                user_input = "Use get_session_info to show current session information"
            
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
                user_id="demo_user",
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
            state_service.complete_session(session_id)
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            if config.debug_mode:
                import traceback
                traceback.print_exc()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n>> Starting ADK Advanced Example...")
    print("Make sure you're authenticated: gcloud auth application-default login\n")
    
    asyncio.run(interactive_chat())
