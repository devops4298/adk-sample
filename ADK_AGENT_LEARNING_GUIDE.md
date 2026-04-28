# 🎯 Complete ADK Agent Learning Guide

> **Comprehensive guide based on analyzing 71 production-ready agents from the ADK samples repository**

---

## 📚 Table of Contents

1. [Learning Roadmap](#-learning-roadmap)
2. [Level 1: Foundations](#-level-1-foundations)
3. [Level 2: Multi-Agent Orchestration](#-level-2-multi-agent-orchestration)
4. [Level 3: Workflow Patterns](#-level-3-workflow-patterns)
5. [Level 4: Tool Integration](#-level-4-tool-integration)
6. [Level 5: Callbacks & State Management](#-level-5-callbacks--state-management)
7. [Level 6: Testing & Evaluation](#-level-6-testing--evaluation)
8. [Level 7: Real-Time & Conversational](#-level-7-real-time--conversational)
9. [Level 8: Production Patterns](#-level-8-production-patterns)
10. [Comprehensive Cheat Sheet](#-comprehensive-cheat-sheet)
11. [Recommended Learning Path](#-recommended-learning-path)

---

## 📚 Learning Roadmap

| Level | Concepts | Example Agents |
|-------|----------|----------------|
| **1. Foundations** | Basic agent structure, tools, prompts | `fun-facts`, `currency-agent` |
| **2. Multi-Agent** | Sub-agents, delegation, orchestration | `customer-service`, `travel-concierge`, `supply-chain` |
| **3. Workflows** | Sequential, parallel, loops, graphs | `workflows-sequential`, `story_teller`, `blog-writer` |
| **4. Tools & Integration** | Custom tools, MCP, external APIs, RAG | `data-science`, `RAG`, `deep-search` |
| **5. State & Memory** | Callbacks, session state, persistence | `small-business-loan-agent`, `policy-as-code`, `memory-bank` |
| **6. Testing & Eval** | Evaluation framework, test data | `customer-service/eval`, `travel-concierge/eval` |
| **7. Real-Time** | WebSocket, streaming, HITL | `realtime-conversational-agent`, `bidi-demo`, `workflows-HITL_concierge` |
| **8. Production** | Domain-specific, compliance, observability | `medical-pre-authorization`, `invoice-processing`, `financial-advisor` |

---

## 🔰 Level 1: Foundations

### 1.1 Basic Agent Structure (`fun-facts`)

**The simplest ADK agent pattern:**

```python
from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.tools import google_search

root_agent = Agent(
    name="Facts",                           # Agent identifier
    model="gemini-flash-latest",            # LLM model
    instruction="Provide mind-blowing...",  # System prompt
    description="An Agent for fun facts",   # For orchestration
    tools=[google_search],                  # Available tools
)

app = App(name="fun_facts", root_agent=root_agent)  # Deployment wrapper
```

**Key Components:**

| Component | Purpose |
|-----------|---------|
| `name` | Unique identifier for the agent |
| `model` | LLM model to use (Gemini variants) |
| `instruction` | System prompt defining behavior |
| `description` | Helps parent agents decide when to delegate |
| `tools` | List of callable functions/tools |
| `App` | Wraps agent for deployment |

**📁 Reference:** `python/agents/fun-facts/fun_facts/agent.py`

---

### 1.2 MCP Tool Integration (`currency-agent`)

**External tool server via Model Context Protocol:**

```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import StreamableHTTPConnectionParams
from google.adk.a2a import to_a2a

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="currency_agent",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
            )
        )
    ],
)

# Make agent discoverable by other agents (Agent-to-Agent protocol)
a2a_app = to_a2a(root_agent, port=10000)
```

**MCP Server Tool Definition:**

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-currency")

@mcp.tool()
def get_exchange_rate(
    currency_from: str = "USD",
    currency_to: str = "EUR",
    currency_date: str = "latest",
):
    """Docstring becomes tool description for the LLM."""
    # Implementation with external API calls...
    response = httpx.get(f"https://api.frankfurter.app/{currency_date}")
    return response.json()
```

**Key Learnings:**
- `MCPToolset` connects to external tool servers via HTTP
- `to_a2a()` enables Agent-to-Agent protocol for inter-agent discovery
- Tool docstrings automatically become the schema description for the LLM

**📁 Reference:** `python/agents/currency-agent/currency_agent/agent.py`

---

### 1.3 Prompt Engineering Patterns

**Pattern A: Persona-based prompts**
```python
instruction="You are a technical blogging assistant with expertise in software development..."
```

**Pattern B: Workflow instructions (numbered steps)**
```python
instruction="""
Your workflow is as follows:
1. **Analyze Codebase:** If provided, use the `analyze_codebase` tool
2. **Plan:** Use the `robust_blog_planner` tool to create an outline
3. **Refine:** Continue to refine until the user approves
4. **Write:** Use the `robust_blog_writer` tool to generate content
5. **Edit:** Use `blog_editor` for final polishing
"""
```

**Pattern C: Boundary-setting prompts**
```python
instruction="""
You are a specialized assistant for currency conversions.
If the user asks about anything other than currency conversion or exchange rates,
politely state that you cannot help with that topic and can only assist with 
currency-related queries. Do not attempt to answer unrelated questions.
"""
```

**Pattern D: Template variables (state injection)**
```python
instruction="""
You are writing the NEXT chapter of the story.

_CURRENT_STORY_STARTS_
{{current_story}}
_CURRENT_STORY_ENDS_

Your writing style should be easy and engaging to read.
"""
```

> **Note:** `{{state_key}}` syntax injects values from session state into prompts at runtime.

---

## 🔗 Level 2: Multi-Agent Orchestration

### 2.1 Four Orchestration Patterns

| Pattern | Class | Use Case | Example Agent |
|---------|-------|----------|---------------|
| **Single + Callbacks** | `Agent` | Simple workflows with hooks | `customer-service` |
| **Hierarchical Delegation** | `Agent.sub_agents=[]` | Phase-based user journeys | `travel-concierge` |
| **Agents-as-Tools** | `AgentTool()` | Expert consultation | `supply-chain` |
| **Sequential Pipeline** | `SequentialAgent` | Fixed-order processing | `llm-auditor` |

---

### 2.2 Pattern A: Single Agent with Callbacks (`customer-service`)

```
Root Agent → [Tools + Callbacks]
```

- **No sub-agents** - Uses a single `Agent` with extensive tool library
- Orchestration via **callbacks**: `before_tool`, `after_tool`, `before_agent`, `before_model`
- Tools handle all functionality (cart management, scheduling, recommendations)
- State managed through `callback_context.state`

```python
from google.adk.agents import Agent

root_agent = Agent(
    name="customer_service_agent",
    model="gemini-2.5-flash",
    instruction=CUSTOMER_SERVICE_PROMPT,
    tools=[
        get_product_recommendations,
        add_to_cart,
        remove_from_cart,
        schedule_delivery,
        apply_discount,
    ],
    before_agent_callback=before_agent,
    before_tool_callback=before_tool,
    after_tool_callback=after_tool,
    before_model_callback=rate_limit_callback,
)
```

**📁 Reference:** `python/agents/customer-service/customer_service/agent.py`

---

### 2.3 Pattern B: Hierarchical Delegation (`travel-concierge`)

```
Root Agent
├── inspiration_agent (sub_agent)
├── planning_agent (sub_agent) → uses AgentTool for nested agents
├── booking_agent (sub_agent)
├── pre_trip_agent (sub_agent)
├── in_trip_agent (sub_agent) → has its own sub_agents
└── post_trip_agent (sub_agent)
```

```python
from google.adk.agents import Agent

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    instruction="""
    You are a travel concierge. Based on the user's request:
    - If user asks about vacation inspiration... transfer to `inspiration_agent`
    - If user asks about finding flights/hotels... transfer to `planning_agent`
    - If user is ready to book... transfer to `booking_agent`
    - If user needs pre-trip help... transfer to `pre_trip_agent`
    - If user is currently traveling... transfer to `in_trip_agent`
    - If user just returned... transfer to `post_trip_agent`
    """,
    sub_agents=[
        inspiration_agent,
        planning_agent,
        booking_agent,
        pre_trip_agent,
        in_trip_agent,
        post_trip_agent,
    ],
)
```

**Transfer Control Flags:**

```python
itinerary_agent = Agent(
    name="itinerary_agent",
    disallow_transfer_to_parent=True,   # Cannot return control up
    disallow_transfer_to_peers=True,    # Cannot transfer to siblings
)
```

**📁 Reference:** `python/agents/travel-concierge/travel_concierge/agent.py`

---

### 2.4 Pattern C: Agents-as-Tools (`supply-chain`)

```
Root Agent (LlmAgent)
├── AgentTool(demand_sense_agent)
├── AgentTool(ops_insight_agent)
├── AgentTool(market_pulse_agent)
├── AgentTool(chart_generator_agent)
└── AgentTool(weather_report_agent)
```

```python
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from google.adk.planners import BuiltInPlanner

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="supply_chain_agent",
    instruction="You are a supply chain analyst. Use the available tools to answer questions.",
    tools=[
        AgentTool(demand_sense_agent),    # Domain expert for demand forecasting
        AgentTool(ops_insight_agent),     # Operations data analyst (NL2SQL)
        AgentTool(market_pulse_agent),    # Real-time market researcher
        AgentTool(chart_generator_agent), # Visualization expert
        AgentTool(weather_report_agent),  # Weather impact analyst
    ],
    planner=BuiltInPlanner(thinking_config=config.thinking_config),
)
```

**Key Difference from `sub_agents`:**
- `sub_agents` = Agent transfer (control passes to sub-agent)
- `AgentTool` = Tool invocation (root agent maintains control, sub-agent returns result)

**📁 Reference:** `python/agents/supply-chain/supply_chain/agent.py`

---

### 2.5 Pattern D: Sequential Pipeline (`llm-auditor`)

```
SequentialAgent
├── critic_agent (step 1: fact-check claims)
└── reviser_agent (step 2: fix inaccuracies)
```

```python
from google.adk.agents import SequentialAgent, LlmAgent

critic_agent = LlmAgent(
    name="critic_agent",
    model="gemini-2.5-flash",
    instruction="Analyze the text and identify any factual claims. Verify each claim using search.",
    tools=[google_search],
    after_model_callback=render_reference_callback,
)

reviser_agent = LlmAgent(
    name="reviser_agent",
    model="gemini-2.5-flash",
    instruction="Based on the critic's findings, revise the text to fix any inaccuracies.",
)

audit_pipeline = SequentialAgent(
    name="llm_auditor",
    description="Fact-checks and revises LLM-generated content",
    sub_agents=[
        critic_agent,   # Step 1
        reviser_agent,  # Step 2
    ],
)
```

**📁 Reference:** `python/agents/llm-auditor/llm_auditor/agent.py`

---

## 🔄 Level 3: Workflow Patterns

### 3.1 Workflow Primitives

| Class | Purpose | Key Feature |
|-------|---------|-------------|
| `SequentialAgent` | Ordered sub-agent execution | Agents run one after another |
| `ParallelAgent` | Concurrent sub-agent execution | Agents run simultaneously |
| `LoopAgent` | Iterate until condition | Repeats until `escalate=True` |
| `WorkflowAgent` | Graph-based edge definitions | Complex routing with conditions |
| `ParallelWorker` | Fan-out single agent over list | One agent, multiple inputs |

---

### 3.2 Sequential + Parallel + Loop (`story_teller`)

**Architecture:**
```
SequentialAgent (root)
├── prompt_enhancer
├── LoopAgent (story_loop)
│   └── SequentialAgent (chapter_cycle)
│       ├── ParallelAgent (parallel_writers)
│       │   ├── creative_writer (temp=0.9)
│       │   └── focused_writer (temp=0.2)
│       └── critique_agent
└── editor_agent
```

```python
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent, LlmAgent
from google.genai import types

# High temperature for creativity
creative_writer = LlmAgent(
    name="CreativeWriter",
    model="gemini-2.5-flash",
    generate_content_config=types.GenerateContentConfig(temperature=0.9),
    instruction="Write a creative, unexpected chapter with vivid imagery.",
    output_key="creative_candidate",
)

# Low temperature for consistency
focused_writer = LlmAgent(
    name="FocusedWriter",
    model="gemini-2.5-flash",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    instruction="Write a consistent, logical chapter that follows the plot.",
    output_key="focused_candidate",
)

# Run both writers in parallel
parallel_writers = ParallelAgent(
    name="ParallelChapterGenerators",
    sub_agents=[creative_writer, focused_writer],
)

# Critique selects the best chapter
critique_agent = LlmAgent(
    name="CritiqueAgent",
    instruction="Compare {{creative_candidate}} and {{focused_candidate}}. Select the best one.",
    output_key="current_story",
)

# Generate → Critique cycle
chapter_cycle = SequentialAgent(
    name="ChapterCycle",
    sub_agents=[parallel_writers, critique_agent],
)

# Repeat N times
story_loop = LoopAgent(
    name="StoryLoop",
    sub_agents=[chapter_cycle],
    max_iterations=5,
)

# Full pipeline: enhance prompt → loop chapters → final edit
root_agent = SequentialAgent(
    name="StoryWorkflow",
    sub_agents=[prompt_enhancer, story_loop, editor_agent],
)
```

**📁 Reference:** `python/agents/story_teller/story_teller_agent/agent.py`

---

### 3.3 LoopAgent with Validation (`blog-writer`)

**Pattern:** Loop until validation passes, then escalate to exit.

```python
from google.adk.agents import LoopAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from typing import AsyncGenerator

class OutlineValidationChecker(BaseAgent):
    """Custom agent that checks if blog outline is valid."""
    
    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Check if outline exists in state
        if context.session.state.get("blog_outline"):
            # Validation passed - escalate to exit the loop
            yield Event(
                author=self.name,
                actions=EventActions(escalate=True),
            )
        else:
            # Validation failed - continue looping
            yield Event(author=self.name)


robust_blog_planner = LoopAgent(
    name="robust_blog_planner",
    description="Retries blog planning until outline is valid",
    sub_agents=[
        blog_planner,                                    # Generates outline
        OutlineValidationChecker(name="outline_checker"), # Validates
    ],
    max_iterations=3,
    after_agent_callback=suppress_output_callback,
)
```

**Key Concept:** `EventActions(escalate=True)` breaks out of the loop.

**📁 Reference:** `python/agents/blog-writer/blogger_agent/sub_agents/blog_planner.py`

---

### 3.4 WorkflowAgent with Routing (`workflow-concurrent_research_writer`)

**Pattern A: Fan-out/Fan-in with ParallelWorker**

```python
from google.adk.agents import WorkflowAgent
from google.adk.agents.parallel_worker import ParallelWorker

async def start_node(ctx):
    """Yields list of items to fan out over."""
    platforms = ["X", "LinkedIn", "Reddit", "Medium"]
    yield Event(state={"platforms": platforms})

research_workflow = WorkflowAgent(
    name="research_workflow",
    edges=[
        (START, start_node, ParallelWorker(research_worker_agent), distill_agent, save_node),
    ],
)
```

**Pattern B: Conditional Routing**

```python
from google.adk.events import Event

async def route_changer(ctx):
    """Routes to different nodes based on condition."""
    platform = ctx.state.get("current_platform")
    yield Event(route=platform)  # Returns "X", "LINKEDIN", or "MEDIUM"

blog_workflow = WorkflowAgent(
    name="blog_workflow",
    edges=[
        (START, start_blog, generate_blog_post_agent, route_changer),
        # Conditional edges: (source, target, "CONDITION")
        (route_changer, post_to_x, "X"),
        (route_changer, post_to_linkedin, "LINKEDIN"),
        (route_changer, post_to_medium, "MEDIUM"),
    ],
)
```

**Pattern C: Composable Workflows**

```python
root_agent = WorkflowAgent(
    name="root_agent",
    rerun_on_resume=True,
    edges=[
        ("START", research_workflow, blog_workflow),  # Workflows as nodes
    ],
)
```

**📁 Reference:** `python/agents/workflow-concurrent_research_writer/agent.py`

---

### 3.5 Hierarchical Workflow (`hierarchical-workflow-automation`)

```python
from google.adk.agents import SequentialAgent, Agent

# Level 3: Leaf agents
haiku_writer_agent = LlmAgent(
    name="haiku_writer",
    instruction="Write a haiku about the order.",
)

# Level 2: Email agent with nested sub-agent
email_agent = Agent(
    name="email_agent",
    instruction="Draft and send confirmation email.",
    tools=[send_email],
    sub_agents=[haiku_writer_agent],
)

# Level 2: Other specialized agents
store_database_agent = Agent(name="store_database", tools=[query_orders])
calendar_agent = Agent(name="calendar", tools=[create_event])

# Level 1: Sequential workflow
delivery_workflow_agent = SequentialAgent(
    name="delivery_workflow_agent",
    sub_agents=[store_database_agent, calendar_agent, email_agent],
)

# Level 0: Root agent
root_agent = Agent(
    name="root_agent",
    instruction="Help customers with their cookie deliveries.",
    sub_agents=[delivery_workflow_agent],
)
```

**📁 Reference:** `python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/agent.py`

---

## 🛠️ Level 4: Tool Integration

### 4.1 Tool Definition Patterns

#### Pattern A: Simple Python Function

```python
def execute_bigquery_sql(sql: str) -> str:
    """Executes a BigQuery SQL query and returns results as JSON.
    
    Args:
        sql: The SQL query to execute.
        
    Returns:
        JSON string of query results.
    """
    from google.cloud import bigquery
    
    client = bigquery.Client()
    results = client.query(sql).result()
    return json.dumps([dict(row) for row in results])
```

#### Pattern B: Context-Aware Tool with `ToolContext`

```python
from google.adk.tools import ToolContext

def bigquery_nl2sql(question: str, tool_context: ToolContext) -> str:
    """Generates SQL from natural language question.
    
    Args:
        question: Natural language question about data.
        tool_context: ADK tool context for state access.
        
    Returns:
        Generated SQL query string.
    """
    # Read from shared state
    schema = tool_context.state["database_settings"]["bigquery"]["schema"]
    
    # Generate SQL using LLM
    sql = generate_sql_with_llm(question, schema)
    
    # Write to shared state for other tools/agents
    tool_context.state["sql_query"] = sql
    tool_context.state["last_question"] = question
    
    return sql
```

#### Pattern C: AgentTool Wrapper

```python
from google.adk.tools import AgentTool

async def call_bigquery_agent(question: str, tool_context: ToolContext):
    """Delegates complex data questions to specialized BigQuery agent.
    
    Args:
        question: Natural language question.
        tool_context: ADK tool context.
        
    Returns:
        Agent's response with query results.
    """
    agent_tool = AgentTool(agent=bigquery_agent)
    
    result = await agent_tool.run_async(
        args={"request": question}, 
        tool_context=tool_context
    )
    
    # Store result in state for parent agent
    tool_context.state["bigquery_output"] = result
    return result
```

#### Pattern D: FunctionTool Wrapper

```python
from google.adk.tools import FunctionTool

def save_blog_post_to_file(title: str, content: str) -> str:
    """Saves blog post to a markdown file."""
    filename = f"{title.lower().replace(' ', '_')}.md"
    with open(filename, 'w') as f:
        f.write(f"# {title}\n\n{content}")
    return f"Saved to {filename}"

# Register with agent
agent = Agent(
    tools=[
        FunctionTool(save_blog_post_to_file),
        FunctionTool(analyze_codebase),
    ],
)
```

---

### 4.2 Built-in ADK Toolsets

#### BigQuery Toolset

```python
from google.adk.tools.bigquery_toolset import (
    BigQueryToolset, 
    BigQueryToolConfig, 
    WriteMode
)

bigquery_toolset = BigQueryToolset(
    tool_filter=["execute_sql"],  # Only expose execute_sql tool
    bigquery_tool_config=BigQueryToolConfig(
        write_mode=WriteMode.BLOCKED,  # Prevent INSERT/UPDATE/DELETE
        application_name="my_agent",
    ),
)

agent = LlmAgent(
    model="gemini-2.5-flash",
    tools=[bigquery_toolset],
)
```

#### Vertex AI RAG Retrieval

```python
from google.adk.tools import VertexAiRagRetrieval
from vertexai import rag

ask_vertex_retrieval = VertexAiRagRetrieval(
    name="retrieve_documentation",
    description="Retrieves relevant documentation from the knowledge base.",
    rag_resources=[
        rag.RagResource(
            rag_corpus="projects/123/locations/us-central1/ragCorpora/456"
        )
    ],
    similarity_top_k=10,              # Return top 10 results
    vector_distance_threshold=0.6,    # Minimum similarity
)

agent = LlmAgent(tools=[ask_vertex_retrieval])
```

#### Google Search

```python
from google.adk.tools import google_search

agent = Agent(
    model="gemini-2.5-flash",
    tools=[google_search],  # Built-in web search
)
```

**📁 References:**
- `python/agents/data-science/data_science/sub_agents/bigquery/agent.py`
- `python/agents/RAG/rag/agent.py`

---

### 4.3 MCP Toolbox Integration (AlloyDB)

```python
from toolbox_langchain import ToolboxSyncClient

def get_toolbox_client():
    """Initialize MCP Toolbox client for database access."""
    MCP_TOOLBOX_HOST = os.getenv("MCP_TOOLBOX_HOST", "localhost")
    MCP_TOOLBOX_PORT = os.getenv("MCP_TOOLBOX_PORT", "8080")
    
    if MCP_TOOLBOX_HOST in ["localhost", "127.0.0.1"]:
        toolbox_url = f"http://{MCP_TOOLBOX_HOST}:{MCP_TOOLBOX_PORT}"
        return ToolboxSyncClient(toolbox_url)
    else:
        # Production: with authentication
        toolbox_url = f"https://{MCP_TOOLBOX_HOST}"
        auth_token = get_google_id_token(toolbox_url)
        return ToolboxSyncClient(
            toolbox_url,
            client_headers={"Authorization": auth_token},
        )

def run_alloydb_query(sql: str, tool_context: ToolContext) -> dict:
    """Execute SQL query via MCP Toolbox."""
    client = get_toolbox_client()
    execute_sql_tool = client.load_tool("execute_sql")
    results = execute_sql_tool(sql)
    tool_context.state["query_result"] = results
    return {"query_result": results}
```

**📁 Reference:** `python/agents/data-science/data_science/sub_agents/alloydb/tools.py`

---

### 4.4 Tool Error Handling

#### Exception Wrapper Decorator

```python
def exception_wrapper(func):
    """Catches exceptions and returns them as error strings."""
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return f"Error in {func.__name__}: {str(e)}"
    return wrapped

@exception_wrapper
def risky_database_operation(query: str):
    # If this fails, returns error string instead of crashing
    return execute_query(query)
```

#### DML/DDL Restriction

```python
import re

def run_safe_query(sql: str, tool_context: ToolContext) -> dict:
    """Execute read-only SQL queries."""
    result = {"query_result": "", "error_message": ""}
    
    # Block dangerous operations
    if re.search(
        r"(?i)(update|delete|drop|insert|create|alter|truncate|merge)",
        sql,
    ):
        result["error_message"] = "DML/DDL operations not allowed."
        return result
    
    try:
        result["query_result"] = execute_query(sql)
    except Exception as e:
        result["error_message"] = f"Query error: {e}"
    
    return result
```

#### Structured Error Response

```python
def robust_tool(input: str, tool_context: ToolContext) -> dict:
    """Tool with structured success/error response."""
    response = {
        "success": False,
        "data": None,
        "error": None,
    }
    
    try:
        response["data"] = process(input)
        response["success"] = True
    except ValidationError as e:
        response["error"] = f"Validation failed: {e}"
    except TimeoutError as e:
        response["error"] = f"Operation timed out: {e}"
    except Exception as e:
        response["error"] = f"Unexpected error: {e}"
    
    return response
```

---

## 💾 Level 5: Callbacks & State Management

### 5.1 Callback Types Overview

| Callback | When Triggered | Return Type | Use Case |
|----------|---------------|-------------|----------|
| `before_agent_callback` | Before agent starts | `None` or `Content` | Input validation, state initialization |
| `after_agent_callback` | After agent completes | `None` or `Content` | Output validation, logging, memory storage |
| `before_tool_callback` | Before tool executes | `None` or `dict` | Tool gating, auto-approval, validation |
| `after_tool_callback` | After tool executes | `None` or `dict` | Side effects, response transformation |
| `before_model_callback` | Before LLM call | `None` | Rate limiting, request sanitization |

---

### 5.2 Before Agent Callback

**Use Case:** Extract required identifiers, validate input, initialize state.

```python
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
import re

async def before_agent_callback(
    callback_context: CallbackContext
) -> types.Content | None:
    """Extract loan request ID before processing."""
    
    # Check if we already have the ID
    if callback_context.state.get("loan_request_id"):
        return None  # Continue to agent
    
    # Try to extract from user message
    user_message = callback_context.user_content.parts[0].text
    match = re.search(r"SBL-\d{4}-\d{5}", user_message)
    
    if match:
        callback_context.state["loan_request_id"] = match.group()
        return None  # Continue to agent
    
    # Short-circuit with error response (agent won't run)
    return types.Content(
        parts=[types.Part(text="Please provide a valid loan request ID (e.g., SBL-2025-00142)")]
    )
```

**📁 Reference:** `python/agents/small-business-loan-agent/small_business_loan_agent/callbacks/`

---

### 5.3 Before Tool Callback

**Use Case:** Validate tool arguments, enforce business rules, auto-approve actions.

```python
from google.adk.tools import BaseTool, ToolContext

MAX_DISCOUNT_RATE = 0.1  # 10% max auto-approval

def before_tool_callback(
    tool: BaseTool, 
    args: dict, 
    tool_context: ToolContext
) -> dict | None:
    """Gate tool execution based on business rules."""
    
    # Check process status
    if tool_context.state.get("process_status") == "halted":
        return {"error": "Process is halted pending approval"}
    
    # Auto-approve small discounts
    if tool.name == "apply_discount":
        discount_rate = args.get("rate", 0)
        if discount_rate <= MAX_DISCOUNT_RATE:
            return {
                "status": "auto_approved",
                "message": f"Discount of {discount_rate*100}% auto-approved",
            }
    
    # Validate customer ID matches session
    if "customer_id" in args:
        session_customer = tool_context.state.get("customer_profile", {}).get("customer_id")
        if args["customer_id"] != session_customer:
            return {"error": "Customer ID mismatch"}
    
    return None  # Continue with normal tool execution
```

**📁 Reference:** `python/agents/customer-service/customer_service/tools/callbacks.py`

---

### 5.4 After Agent Callback

**Use Case:** Validate response quality, persist state, trigger memory storage.

```python
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

async def after_agent_callback(
    callback_context: CallbackContext
) -> types.Content | None:
    """Validate response with LLM-as-Judge pattern."""
    
    response = callback_context.agent_response
    
    # Use another LLM to validate response quality
    validation_prompt = f"""
    Evaluate this response for accuracy and helpfulness:
    {response}
    
    Grade: PASS or FAIL
    Reason: <brief explanation>
    """
    
    validation_result = await validate_with_llm(validation_prompt)
    
    if validation_result["grade"] == "FAIL":
        # Log the issue
        log_quality_issue(response, validation_result["reason"])
        
        # Replace response
        return types.Content(
            parts=[types.Part(text="I apologize, let me reconsider and provide a better answer...")]
        )
    
    # Pass through original response
    return None
```

**Memory Storage Callback:**

```python
async def generate_memories_callback(callback_context: CallbackContext):
    """Store conversation in memory bank after agent turn."""
    
    # Get session events
    session = callback_context._invocation_context.session
    
    # Send to Memory Bank for long-term storage
    await callback_context.add_session_to_memory(session)
```

**📁 Reference:** `python/agents/memory-bank/memory_bank/agent.py`

---

### 5.5 Before Model Callback

**Use Case:** Rate limiting, request modification.

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
import time

RATE_LIMIT = 10  # requests per minute

def rate_limit_callback(
    callback_context: CallbackContext, 
    llm_request: LlmRequest
) -> None:
    """Implement rate limiting for LLM calls."""
    
    state = callback_context.state
    
    # Initialize tracking
    if "request_count" not in state:
        state["request_count"] = 0
        state["timer_start"] = time.time()
    
    # Check if over quota
    if state["request_count"] >= RATE_LIMIT:
        elapsed = time.time() - state["timer_start"]
        if elapsed < 60:
            sleep_time = 60 - elapsed
            print(f"Rate limit reached. Sleeping for {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        # Reset counter
        state["request_count"] = 0
        state["timer_start"] = time.time()
    
    state["request_count"] += 1
```

---

### 5.6 Memory Management Patterns

#### Pattern A: Vertex AI Memory Bank

```python
from google.adk.memory import (
    MemoryBankConfig, 
    CustomizationConfig, 
    MemoryTopic,
    ManagedMemoryTopic, 
    ManagedTopicEnum
)
from google.adk.tools.memory import PreloadMemoryTool, LoadMemoryTool

# Configure memory topics
memory_config = MemoryBankConfig(
    customization_configs=[
        CustomizationConfig(
            memory_topics=[
                MemoryTopic(managed_memory_topic=ManagedMemoryTopic(
                    managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO
                )),
                MemoryTopic(managed_memory_topic=ManagedMemoryTopic(
                    managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES
                )),
                MemoryTopic(managed_memory_topic=ManagedMemoryTopic(
                    managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS
                )),
            ],
        ),
    ],
)

# Agent with memory tools
agent = Agent(
    name="memory_agent",
    tools=[
        PreloadMemoryTool(),  # Auto-retrieve memories at turn start
        LoadMemoryTool(),     # On-demand memory retrieval
    ],
    after_agent_callback=generate_memories_callback,
)
```

**📁 Reference:** `python/agents/memory-bank/memory_bank/agent.py`

#### Pattern B: Custom Firestore Memory with Vector Search

```python
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from vertexai.language_models import TextEmbeddingModel

db = firestore.Client()
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

def save_to_memory(item_id: str, content: str, metadata: dict):
    """Save item with vector embedding for semantic search."""
    
    # Generate embedding
    embedding = embedding_model.get_embeddings([content])[0].values
    
    doc = {
        "item_id": item_id,
        "content": content,
        "metadata": metadata,
        "embedding": Vector(embedding),
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    
    db.collection("memories").document(item_id).set(doc)

def find_similar(query: str, limit: int = 5) -> list:
    """Find semantically similar items."""
    
    query_embedding = embedding_model.get_embeddings([query])[0].values
    
    results = db.collection("memories").find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=limit,
    )
    
    return [doc.to_dict() for doc in results]
```

**📁 Reference:** `python/agents/policy-as-code/policy_as_code_agent/memory.py`

---

### 5.7 State Flow with `output_key`

```python
# Agent 1: Writes analysis to state
data_analyst = LlmAgent(
    name="data_analyst",
    instruction="Analyze market data for the given ticker.",
    tools=[google_search],
    output_key="market_analysis",  # Output stored in state["market_analysis"]
)

# Agent 2: Reads from state, writes strategy
trading_analyst = LlmAgent(
    name="trading_analyst",
    instruction="""
    Based on the market analysis: {{market_analysis}}
    
    Develop a trading strategy.
    """,
    output_key="trading_strategy",
)

# Agent 3: Reads both previous outputs
risk_analyst = LlmAgent(
    name="risk_analyst",
    instruction="""
    Market Analysis: {{market_analysis}}
    Trading Strategy: {{trading_strategy}}
    
    Assess the risks of this strategy.
    """,
    output_key="risk_assessment",
)

# Pipeline automatically passes state between agents
pipeline = SequentialAgent(
    name="financial_analysis_pipeline",
    sub_agents=[data_analyst, trading_analyst, risk_analyst],
)
```

**📁 Reference:** `python/agents/financial-advisor/financial_advisor/agent.py`

---

## ✅ Level 6: Testing & Evaluation

### 6.1 Test Data Format

#### Simple Array Format (`*.test.json`)

```json
[
  {
    "query": "What is the exchange rate for USD to EUR?",
    "expected_tool_use": [
      {
        "tool_name": "get_exchange_rate",
        "tool_input": {
          "currency_from": "USD",
          "currency_to": "EUR"
        }
      }
    ],
    "reference": "The current exchange rate is approximately 0.92 EUR per USD."
  },
  {
    "query": "Convert 100 dollars to Japanese yen",
    "expected_tool_use": [
      {
        "tool_name": "get_exchange_rate",
        "tool_input": {
          "currency_from": "USD",
          "currency_to": "JPY"
        }
      }
    ],
    "reference": "100 USD is approximately 15,000 JPY."
  }
]
```

#### Multi-Turn Conversation Format

```json
{
  "eval_set_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Travel Booking Full Flow",
  "eval_cases": [
    {
      "eval_id": "booking/flight_search_to_booking",
      "conversation": [
        {
          "invocation_id": "turn_001",
          "user_content": {
            "parts": [{"text": "I want to book a flight from NYC to London"}],
            "role": "user"
          },
          "final_response": {
            "parts": [{"text": "I found several flight options..."}],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [
              {"name": "search_flights", "args": {"from": "NYC", "to": "LHR"}}
            ],
            "intermediate_responses": [
              ["planning_agent", [{"text": "Searching for flights..."}]]
            ]
          }
        },
        {
          "invocation_id": "turn_002",
          "user_content": {
            "parts": [{"text": "Book the first option"}],
            "role": "user"
          },
          "final_response": {
            "parts": [{"text": "I've booked your flight..."}],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [
              {"name": "book_flight", "args": {"flight_id": "BA123"}}
            ]
          }
        }
      ],
      "session_input": {
        "app_name": "travel_concierge",
        "user_id": "test_user_001",
        "state": {
          "customer_id": "CUST123",
          "loyalty_tier": "gold",
          "preferred_airline": "British Airways"
        }
      }
    }
  ]
}
```

---

### 6.2 Test Configuration (`test_config.json`)

```json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.8,
    "response_match_score": 0.7
  }
}
```

| Metric | Description | Typical Threshold |
|--------|-------------|-------------------|
| `tool_trajectory_avg_score` | Did agent call correct tools with correct args? | 0.1 - 1.0 |
| `response_match_score` | Semantic similarity to reference response | 0.1 - 0.35 |

---

### 6.3 Session Recording Format (`*.session.json`)

```json
{
  "id": "f7e81523-cd34-4202-821e-a1f44d9cef94",
  "app_name": "customer_service_agent",
  "user_id": "test_user",
  "state": {
    "customer_profile": {
      "customer_id": "123",
      "customer_first_name": "Alex",
      "email": "alex.johnson@example.com",
      "loyalty_points": 133
    }
  },
  "events": [
    {
      "content": {
        "parts": [{"text": "I want to return my order"}],
        "role": "user"
      },
      "invocation_id": "xfBN9J9f",
      "author": "user",
      "actions": {"state_delta": {}, "artifact_delta": {}},
      "id": "evt_001",
      "timestamp": 1741218414.968405
    },
    {
      "content": {
        "parts": [
          {"text": "I'd be happy to help with your return."},
          {"function_call": {"name": "get_order_details", "args": {"order_id": "ORD-123"}}}
        ],
        "role": "model"
      },
      "invocation_id": "xfBN9J9f",
      "author": "customer_service_agent",
      "timestamp": 1741218415.123456
    }
  ],
  "last_update_time": 1741218714.258285
}
```

---

### 6.4 Test Runner

```python
# eval/test_eval.py
import pytest
from google.adk.evaluation import AgentEvaluator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable async pytest
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def setup_environment():
    """One-time setup for all tests."""
    # Initialize any required services
    pass


@pytest.mark.asyncio
async def test_customer_service_agent():
    """Evaluate customer service agent against test cases."""
    
    await AgentEvaluator.evaluate(
        agent_module="customer_service_agent",  # Module name
        eval_data_path="eval/eval_data/",       # Path to test files
        num_runs=1,                              # Number of evaluation runs
    )


@pytest.mark.asyncio
async def test_single_case():
    """Test a specific scenario."""
    
    await AgentEvaluator.evaluate(
        agent_module="customer_service_agent",
        eval_data_path="eval/eval_data/return_flow.test.json",
        num_runs=3,  # Run multiple times for consistency check
    )
```

**Run tests:**
```bash
# Run all evaluations
pytest eval/test_eval.py -v

# Run specific test
pytest eval/test_eval.py::test_customer_service_agent -v

# Run with coverage
pytest eval/test_eval.py --cov=customer_service_agent
```

**📁 Reference:** `python/agents/customer-service/eval/test_eval.py`

---

## 🔴 Level 7: Real-Time & Conversational

### 7.1 WebSocket Bidirectional Streaming

**Architecture:** FastAPI backend + WebSocket for real-time audio/video/text

```python
from fastapi import FastAPI, WebSocket
from google.adk.runners import InMemoryRunner
from google.adk.runners.run_config import RunConfig, StreamingMode
from google.adk.live import LiveRequestQueue
from google.genai import types
import asyncio

app = FastAPI()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    
    # Initialize runner and request queue
    runner = InMemoryRunner(agent=root_agent)
    live_request_queue = LiveRequestQueue()
    session_id = f"session_{user_id}"
    
    # Configure real-time streaming
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],  # or ["TEXT"] or ["AUDIO", "TEXT"]
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                prefix_padding_ms=0,
                silence_duration_ms=0,
            )
        ),
    )
    
    async def upstream_task():
        """Client → Agent: Receive input and send to queue."""
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                # Audio data (binary)
                audio_blob = types.Blob(
                    data=message["bytes"], 
                    mime_type="audio/pcm"
                )
                live_request_queue.send_realtime(audio_blob)
                
            elif "text" in message:
                # Text message (JSON)
                data = json.loads(message["text"])
                if data.get("type") == "text":
                    content = types.Content(
                        parts=[types.Part(text=data["text"])]
                    )
                    live_request_queue.send_content(content)
    
    async def downstream_task():
        """Agent → Client: Stream events to websocket."""
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            event_json = event.model_dump_json(exclude_none=True)
            await websocket.send_text(event_json)
    
    # Run both tasks concurrently
    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

**📁 Reference:** `python/agents/realtime-conversational-agent/server/main.py`

---

### 7.2 Human-in-the-Loop with `RequestInput`

**Pattern:** Pause workflow execution and wait for user input.

```python
from google.adk.agents import WorkflowAgent, LlmAgent
from google.adk.events import RequestInput, Event, UserContent
from google.genai import types
from pydantic import BaseModel
from typing import List

# Define structured output
class Activity(BaseModel):
    name: str
    description: str
    duration_hours: float

class ActivitiesList(BaseModel):
    activities: List[Activity]


async def initial_prompt(ctx):
    """Step 1: Request user preferences."""
    yield RequestInput(
        message="""
        Welcome! I'll create a personalized itinerary for you.
        Please provide:
        - City (required)
        - Your interests/hobbies
        - Any specific attractions you've enjoyed before
        """,
        response_schema={"user_response": str}
    )


# LLM agent with structured output
concierge_agent = LlmAgent(
    name="concierge_agent",
    model="gemini-2.5-flash",
    instruction="Create a personalized itinerary based on user preferences.",
    tools=[google_search],
    output_schema=ActivitiesList,  # Structured output
    output_key="itinerary",
)


async def get_user_feedback(ctx):
    """Step 3: Display results and request feedback."""
    itinerary = ctx.state.get("itinerary")
    
    # Format itinerary for display
    formatted = "\n".join([
        f"- {a.name}: {a.description} ({a.duration_hours}h)"
        for a in itinerary.activities
    ])
    
    yield RequestInput(
        message=f"""
        Here's your personalized itinerary:
        
        {formatted}
        
        Would you like any changes? (or say 'done' to finalize)
        """,
        response_schema={"feedback": str}
    )


async def process_feedback(ctx):
    """Step 4: Transform feedback into agent input."""
    response = ctx.state.get("_request_input_response")
    feedback = response.get("feedback", "")
    
    if feedback.lower() == "done":
        # End the workflow
        yield Event(route="DONE")
    else:
        # Continue with refinement
        yield UserContent(parts=[types.Part(text=feedback)])


# Workflow with loop for iterative refinement
root_agent = WorkflowAgent(
    name="hitl_concierge",
    rerun_on_resume=True,  # Re-execute nodes when resumed
    edges=[
        ("START", initial_prompt, concierge_agent, get_user_feedback, process_feedback),
        (process_feedback, concierge_agent),  # Loop back for refinement
    ],
)
```

**📁 Reference:** `python/agents/workflows-HITL_concierge/agent.py`

---

### 7.3 Server-Sent Events (SSE) Streaming

**Pattern:** HTTP streaming for long-running research tasks.

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.post("/research")
async def research_endpoint(request: ResearchRequest):
    """Stream research progress via SSE."""
    
    async def event_generator():
        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=request.session_id,
            new_message=types.Content(parts=[types.Part(text=request.query)]),
        ):
            # Format as SSE
            event_data = {
                "agent": event.author,
                "content": event.content.parts[0].text if event.content else None,
                "type": "progress" if not event.is_final else "complete",
            }
            yield f"data: {json.dumps(event_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Frontend SSE handling (JavaScript):**

```javascript
const eventSource = new EventSource('/research');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'progress') {
        updateProgressUI(data.agent, data.content);
    } else if (data.type === 'complete') {
        displayFinalResult(data.content);
        eventSource.close();
    }
};

eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
};
```

**📁 Reference:** `python/agents/deep-search/app/agent.py`

---

## 🏭 Level 8: Production Patterns

### 8.1 Domain-Specific Agent Design

| Domain | Architecture | Key Features |
|--------|--------------|--------------|
| **Healthcare** | Hierarchical + Document Processing | Multi-stage extraction, compliance justification, audit trails |
| **Finance** | Sequential Expert Chain | Mandatory disclaimers, risk assessment, regulatory compliance |
| **IT Operations** | External SaaS Integration | OAuth2 authentication, confirmation workflows, ITSM field mapping |
| **Document Processing** | Pipeline + Adaptive Learning | Deterministic rules, impact assessment, SME-guided learning |

---

### 8.2 Compliance Patterns

#### Mandatory Disclaimers (Finance)

```python
FINANCIAL_COORDINATOR_PROMPT = """
Role: Act as a specialized financial advisory assistant.

IMPORTANT: After every response, you MUST display this disclaimer:

---
**Important Disclaimer: For Educational and Informational Purposes Only.**

The information and trading strategy outlines provided by this tool, including 
any analysis, commentary, or potential scenarios, are generated by an AI model 
and are for educational and informational purposes only.

They do not constitute, and should not be interpreted as:
- Financial advice
- Investment recommendations
- Endorsements
- Offers to buy or sell any securities

Google and its affiliates make no representations or warranties of any kind 
about the completeness, accuracy, reliability, or suitability of this information.

Any reliance you place on such information is strictly at your own risk.
---
"""
```

**📁 Reference:** `python/agents/financial-advisor/financial_advisor/prompt.py`

#### Decision Justification (Healthcare)

```python
DATA_ANALYST_INSTRUCTION = """
As an Information Analysis and Report Generator Agent, your role is to 
evaluate pre-authorization requests for medical treatments.

**Process:**
1. **Receive Information:** 
   - User's Insurance Coverage Details
   - User's Medical Records

2. **Analyze and Decide:**
   - Thoroughly review both insurance coverage and medical records
   - Make a clear decision: **"Pass"** or **"Reject"**
   - Provide a detailed reason explicitly referencing:
     * Relevant medical record information
     * Insurance policy eligibility criteria
   
3. **Generate Report:**
   - Create a structured PDF report with decision and justification
   - Include audit trail with timestamps
"""
```

**📁 Reference:** `python/agents/medical-pre-authorization/medical_pre_authorization/subagents/data_analyst/prompt.py`

---

### 8.3 Rate Limiting

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest
import time

class RateLimiter:
    """Token bucket rate limiter for LLM calls."""
    
    def __init__(self, requests_per_minute: int = 10):
        self.rpm = requests_per_minute
        self.tokens = requests_per_minute
        self.last_update = time.time()
    
    def acquire(self):
        """Acquire a token, blocking if necessary."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Replenish tokens
        self.tokens = min(
            self.rpm,
            self.tokens + elapsed * (self.rpm / 60)
        )
        self.last_update = now
        
        if self.tokens < 1:
            sleep_time = (1 - self.tokens) * (60 / self.rpm)
            time.sleep(sleep_time)
            self.tokens = 0
        else:
            self.tokens -= 1

rate_limiter = RateLimiter(requests_per_minute=10)

def rate_limit_callback(
    callback_context: CallbackContext, 
    llm_request: LlmRequest
) -> None:
    """Callback to enforce rate limiting."""
    rate_limiter.acquire()
```

**📁 Reference:** `python/agents/customer-service/customer_service/tools/callbacks.py`

---

### 8.4 Configuration Management

#### Dataclass Configuration

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AgentConfiguration:
    """Centralized configuration for agent behavior."""
    
    # Model settings
    critic_model: str = "gemini-2.5-pro"
    worker_model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    
    # Workflow settings
    max_search_iterations: int = 5
    max_retry_attempts: int = 3
    timeout_seconds: int = 60
    
    # Feature flags
    enable_memory: bool = True
    enable_rate_limiting: bool = True
    debug_mode: bool = False
    
    # API keys (loaded from environment)
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("API_KEY")
    )

# Global configuration instance
config = AgentConfiguration()

# Usage in agent
agent = LlmAgent(
    model=config.worker_model,
    generate_content_config=types.GenerateContentConfig(
        temperature=config.temperature
    ),
)
```

**📁 Reference:** `python/agents/blog-writer/blogger_agent/config.py`

#### Environment-based Configuration

```python
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configuration with defaults
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "default-project")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Feature flags
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8192"))
```

#### Separate File Organization

```
agent/
├── agent.py           # Main agent definition
├── config.py          # Configuration dataclass
├── instructions.py    # Prompt templates
├── tools.py           # Tool definitions
├── callbacks.py       # Callback implementations
├── models.py          # Pydantic models
└── sub_agents/
    ├── __init__.py
    ├── analyst/
    │   ├── agent.py
    │   └── prompt.py
    └── writer/
        ├── agent.py
        └── prompt.py
```

---

### 8.5 Graceful Degradation

```python
import logging

logger = logging.getLogger(__name__)

# Feature availability flags
BIGQUERY_AVAILABLE = False
MCP_AVAILABLE = False

try:
    from google.cloud import bigquery
    bigquery.Client()
    BIGQUERY_AVAILABLE = True
except Exception as e:
    logger.warning(f"BigQuery not available: {e}")

try:
    from toolbox_langchain import ToolboxSyncClient
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("MCP Toolbox not available")


def get_order_details(order_id: str, tool_context: ToolContext) -> dict:
    """Get order with graceful fallback."""
    
    # Try real service first
    if BIGQUERY_AVAILABLE:
        try:
            result = query_bigquery(order_id)
            if result:
                return result
        except Exception as e:
            logger.error(f"BigQuery query failed: {e}")
    
    # Fallback to cached/dummy data
    logger.info("Using fallback data for order retrieval")
    return get_cached_order(order_id) or generate_dummy_order(order_id)
```

**📁 Reference:** `python/agents/hierarchical-workflow-automation/cookie_scheduler_agent/tools.py`

---

## 📋 Comprehensive Cheat Sheet

### Agent Types

```python
# Basic agent
Agent(name, model, instruction, description, tools, sub_agents)

# LLM agent with planner support
LlmAgent(name, model, instruction, tools, planner, output_key, output_schema)

# Sequential pipeline
SequentialAgent(name, sub_agents)

# Parallel execution
ParallelAgent(name, sub_agents)

# Loop with max iterations
LoopAgent(name, sub_agents, max_iterations)

# Graph-based workflow
WorkflowAgent(name, edges, rerun_on_resume)
```

### Tool Patterns

```python
# Built-in tools
tools=[google_search]

# Wrap Python function
tools=[FunctionTool(my_function)]

# Agent as tool
tools=[AgentTool(sub_agent)]

# External MCP server
tools=[MCPToolset(connection_params=StreamableHTTPConnectionParams(url=...))]

# BigQuery toolset
tools=[BigQueryToolset(tool_filter=["execute_sql"], bigquery_tool_config=...)]

# RAG retrieval
tools=[VertexAiRagRetrieval(name=..., rag_resources=[...], similarity_top_k=10)]
```

### Callbacks

```python
Agent(
    before_agent_callback=validate_input,      # Input validation
    after_agent_callback=validate_output,      # Output validation
    before_tool_callback=gate_tool_access,     # Tool gating
    after_tool_callback=handle_side_effects,   # Side effects
    before_model_callback=rate_limit,          # Rate limiting
)
```

### State Management

```python
# Agent writes output to state
output_key="result"

# Tool reads/writes state
tool_context.state["key"] = value
value = tool_context.state.get("key")

# Callback state access
callback_context.state["key"] = value

# Agent state access
context.session.state.get("key")

# Template variable injection
instruction="Use this data: {{state_key}}"
```

### Workflow Control

```python
# Exit loop
EventActions(escalate=True)

# Request user input (HITL)
RequestInput(message="...", response_schema={"field": str})

# Conditional routing
Event(route="CONDITION_NAME")

# Fan-out over list
ParallelWorker(agent)
```

### Evaluation

```python
# Run evaluation
await AgentEvaluator.evaluate(
    agent_module="my_agent",
    eval_data_path="eval/eval_data/",
    num_runs=1,
)
```

---

## 🎓 Recommended Learning Path

### Week 1: Foundations
1. **Day 1-2:** `fun-facts` → Basic agent structure
2. **Day 3-4:** `currency-agent` → MCP tool integration
3. **Day 5-7:** `blog-writer` → FunctionTool, configuration patterns

### Week 2: Multi-Agent & Workflows
4. **Day 8-9:** `llm-auditor` → Sequential pipeline
5. **Day 10-11:** `story_teller` → Parallel + Loop agents
6. **Day 12-14:** `travel-concierge` → Hierarchical delegation

### Week 3: Tools & State
7. **Day 15-16:** `data-science` → BigQuery toolset, context-aware tools
8. **Day 17-18:** `customer-service` → Callbacks deep dive
9. **Day 19-21:** `small-business-loan-agent` → Full production patterns

### Week 4: Advanced
10. **Day 22-23:** `customer-service/eval` → Testing framework
11. **Day 24-25:** `bidi-demo` → Real-time WebSocket
12. **Day 26-28:** `medical-pre-authorization` → Domain-specific compliance

---

## 📁 Quick Reference: Agent Locations

| Agent | Path | Key Concept |
|-------|------|-------------|
| `fun-facts` | `python/agents/fun-facts/` | Basic structure |
| `currency-agent` | `python/agents/currency-agent/` | MCP + A2A |
| `blog-writer` | `python/agents/blog-writer/` | LoopAgent + validation |
| `story_teller` | `python/agents/story_teller/` | Sequential + Parallel + Loop |
| `llm-auditor` | `python/agents/llm-auditor/` | Sequential pipeline |
| `customer-service` | `python/agents/customer-service/` | Callbacks + eval |
| `travel-concierge` | `python/agents/travel-concierge/` | Hierarchical sub-agents |
| `supply-chain` | `python/agents/supply-chain/` | AgentTool pattern |
| `data-science` | `python/agents/data-science/` | BigQuery + RAG tools |
| `small-business-loan-agent` | `python/agents/small-business-loan-agent/` | Full production |
| `memory-bank` | `python/agents/memory-bank/` | Vertex AI Memory |
| `policy-as-code` | `python/agents/policy-as-code/` | Custom Firestore memory |
| `realtime-conversational-agent` | `python/agents/realtime-conversational-agent/` | WebSocket streaming |
| `bidi-demo` | `python/agents/bidi-demo/` | Bidirectional audio |
| `workflows-HITL_concierge` | `python/agents/workflows-HITL_concierge/` | Human-in-the-loop |
| `deep-search` | `python/agents/deep-search/` | Multi-agent research |
| `medical-pre-authorization` | `python/agents/medical-pre-authorization/` | Healthcare compliance |
| `financial-advisor` | `python/agents/financial-advisor/` | Finance disclaimers |
| `invoice-processing` | `python/agents/invoice-processing/` | Document processing |
| `incident-management` | `python/agents/incident-management/` | ServiceNow integration |

---

## 🔬 Level 9: Arize/Phoenix Evaluation & Observability

### 9.1 Phoenix Tracing Setup

**Instrument ADK with Arize for observability:**

```python
# tracing.py
import os
from arize.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from opentelemetry import trace

def instrument_adk_with_arize():
    """Instrument ADK with Arize Phoenix for observability."""
    
    if not os.getenv("ARIZE_SPACE_ID") or not os.getenv("ARIZE_API_KEY"):
        print("Warning: Arize credentials not set")
        return None
    
    # Register Arize tracer provider
    tracer_provider = register(
        space_id=os.getenv("ARIZE_SPACE_ID"),
        api_key=os.getenv("ARIZE_API_KEY"),
        project_name=os.getenv("ARIZE_PROJECT_NAME", "my-adk-agent"),
    )
    
    # Instrument ADK
    GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
    
    return tracer_provider.get_tracer(__name__)
```

**Use in agent:**
```python
from tracing import instrument_adk_with_arize
from openinference.instrumentation import using_session
import uuid

# Initialize tracing
_ = instrument_adk_with_arize()

# Use session tracking
with using_session(session_id=uuid.uuid4()):
    # Agent interactions here
    pass
```

**Required dependencies:**
```
openinference-instrumentation-google-adk>=0.1.0
openinference-instrumentation>=0.1.34
arize-otel>=0.8.2
arize>=7.36.0
```

**📁 Reference:** `python/agents/travel-concierge/travel_concierge/tracing.py`

---

### 9.2 Custom Evaluation Templates (LLM-as-Judge)

**Define ClassificationTemplate for evaluation:**

```python
from phoenix.evals import ClassificationTemplate

# Agent handoff evaluation
AGENT_HANDOFF_TEMPLATE = ClassificationTemplate(
    rails=["correct_handoff", "incorrect_handoff"],
    template="""
You are evaluating agent handoffs in a multi-agent system.

User Query: {query}
Agent Response: {agent_response}
Expected Agent Transfers: {expected_agent_transfers}
Actual Agent Transfers: {actual_agent_transfers}

Classification Guidelines:
- correct_handoff: Agent transferred to correct sub-agent(s) as expected
- incorrect_handoff: Agent failed to transfer or transferred incorrectly

Classify this agent handoff behavior:
""",
)

# Tool usage evaluation
TOOL_USAGE_TEMPLATE = ClassificationTemplate(
    rails=["correct_tools", "incorrect_tools"],
    template="""
You are evaluating tool usage correctness.

User Query: {query}
Expected Tools: {expected_tools}
Actual Tools Used: {actual_tools}
Tool Outputs: {tool_outputs}

Classification Guidelines:
- correct_tools: All necessary tools were called with correct parameters
- incorrect_tools: Missing tools, wrong tools, or incorrect parameters

Classify this tool usage:
""",
)

# Response quality evaluation
RESPONSE_QUALITY_TEMPLATE = ClassificationTemplate(
    rails=["good_response", "poor_response"],
    template="""
You are evaluating response quality.

User Query: {query}
Agent Response: {response}
Expected Behavior: {expected_behavior}

Classification Guidelines:
- good_response: Accurate, helpful, addresses user's needs
- poor_response: Inaccurate, unhelpful, or misses user's intent

Classify this response:
""",
)
```

**📁 Reference:** `python/agents/travel-concierge/eval/arize_eval_templates.py`

---

### 9.3 Custom Evaluator with Phoenix + Arize

```python
import json
import pandas as pd
from phoenix.evals import GeminiModel, llm_classify
from arize.experimental.datasets.experiments.types import EvaluationResult

# Initialize Phoenix model
phoenix_model = GeminiModel(model="gemini-2.0-flash")

def agent_handoff_evaluator(output: str, dataset_row: dict) -> EvaluationResult:
    """Evaluator for agent handoff correctness using LLM-as-judge."""
    try:
        # Parse agent output
        metadata = json.loads(output) if isinstance(output, str) else output
        
        # Create evaluation data
        eval_data = pd.DataFrame([{
            "query": dataset_row.get("query", ""),
            "agent_response": metadata.get("agent_response", ""),
            "expected_agent_transfers": dataset_row.get("expected_agent_transfers", "[]"),
            "actual_agent_transfers": json.dumps(metadata.get("actual_agent_transfers", [])),
        }])
        
        # Run Phoenix LLM classification
        result = llm_classify(
            data=eval_data,
            model=phoenix_model,
            template=AGENT_HANDOFF_TEMPLATE,
            rails=AGENT_HANDOFF_TEMPLATE.rails,
            verbose=False,
        )
        
        # Extract result
        label = result.iloc[0]["label"] if len(result) > 0 else "unknown"
        score = 1.0 if label == "correct_handoff" else 0.0
        
        return EvaluationResult(
            score=score,
            label=label,
            explanation=f"Handoff evaluation: {label}"
        )
    except Exception as e:
        return EvaluationResult(score=0.0, label="error", explanation=str(e))
```

---

### 9.4 Running Arize Experiments

```python
from arize.experimental.datasets import ArizeDatasetsClient

# Initialize client
arize_client = ArizeDatasetsClient(api_key=os.getenv("ARIZE_API_KEY"))

# Create dataset
dataset = arize_client.create_dataset(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    dataset_name="travel_concierge_eval",
    dataset_type="GENERATIVE",
    data=test_data_df,
)

# Define task function (runs agent)
async def task_function(dataset_row: dict) -> str:
    query = dataset_row["query"]
    response = await run_agent(query)
    return json.dumps({
        "agent_response": response.text,
        "actual_agent_transfers": response.transfers,
        "tool_uses": response.tool_calls,
    })

# Run experiment
experiment_result = arize_client.run_experiment(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    dataset_id=dataset["id"],
    task=task_function,
    evaluators=[
        agent_handoff_evaluator,
        tool_usage_evaluator,
        response_quality_evaluator,
    ],
    experiment_name=f"eval_{datetime.now().isoformat()}",
    concurrency=2,
    exit_on_error=False,
)
```

**📁 Reference:** `python/agents/travel-concierge/eval/test_eval_arize.py`

---

### 9.5 ADK Built-in Evaluation Criteria

ADK provides native evaluation via Vertex AI:

| Criterion | Description |
|-----------|-------------|
| `tool_trajectory_avg_score` | Compares tool call sequences |
| `response_match_score` | Rouge-1 similarity scoring |
| `final_response_match_v2` | LLM-based semantic matching |
| `hallucinations_v1` | Hallucination detection |
| `safety_v1` | Safety evaluation |
| `rubric_based_final_response_quality_v1` | Custom rubric evaluation |

```python
# test_config.json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.8,
    "response_match_score": 0.7,
    "hallucinations_v1": {"threshold": 0.5},
    "safety_v1": {"threshold": 0.8}
  }
}
```

**📁 Reference:** `python/notebooks/evaluation/evaluation_criteria_in_adk.ipynb`

---

## 💾 Level 10: Session Storage & Database Persistence

### 10.1 Built-in SessionService Options

| Service | Use Case | Persistence |
|---------|----------|-------------|
| `InMemorySessionService` | Development/Testing | None (volatile) |
| `VertexAiSessionService` | Production (GCP managed) | Vertex AI backend |
| `DatabaseSessionService` | Self-managed databases | SQLite, Cloud SQL, etc. |

```python
from google.adk.sessions import InMemorySessionService, VertexAiSessionService

# Development - in-memory
session_service = InMemorySessionService()

# Production - Vertex AI managed
session_service = VertexAiSessionService(
    project_id="my-project",
    location="us-central1"
)

# Database-backed via URI
from google.adk.apps import get_fast_api_app

app = get_fast_api_app(
    agents_dir=".",
    session_service_uri="sqlite:///./sessions.db",  # SQLite
    # Or: "postgresql://user:pass@host:5432/db"     # PostgreSQL
    # Or: "mysql://user:pass@host:3306/db"          # MySQL
)
```

---

### 10.2 Firestore Workflow State Persistence

**Complete state service for multi-step workflows:**

```python
from google.cloud import firestore
from datetime import datetime
import os

class ProcessStateService:
    """Firestore-backed workflow state management."""
    
    # Step names (match agent names)
    ALL_STEPS = (
        "DocumentExtractionAgent",
        "UnderwritingAgent", 
        "PricingAgent",
        "LoanDecisionAgent",
    )
    
    # Status values
    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_PENDING_APPROVAL = "pending_approval"
    STATUS_ERROR = "error"
    
    # Overall process statuses
    OVERALL_STATUS_ACTIVE = "active"
    OVERALL_STATUS_COMPLETED = "completed"
    OVERALL_STATUS_FAILED = "failed"
    
    def __init__(self, database_name: str = "(default)"):
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.db = firestore.Client(project=project_id, database=database_name)
        self.collection_name = "process_states"
    
    def create_process(self, request_id: str, session_id: str) -> dict:
        """Initialize new process state."""
        steps = {
            step: {
                "status": self.STATUS_NOT_STARTED,
                "completed_at": None,
                "data": None,
            }
            for step in self.ALL_STEPS
        }
        
        process_state = {
            "request_id": request_id,
            "session_id": session_id,
            "current_step": self.ALL_STEPS[0],
            "overall_status": self.OVERALL_STATUS_ACTIVE,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "steps": steps,
            "issues": [],
        }
        
        self.db.collection(self.collection_name).document(request_id).set(process_state)
        return process_state
    
    def update_step(self, request_id: str, step_name: str, status: str, data: dict = None):
        """Update a specific step's status and data."""
        doc_ref = self.db.collection(self.collection_name).document(request_id)
        
        updates = {
            f"steps.{step_name}.status": status,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        
        if status == self.STATUS_COMPLETED:
            updates[f"steps.{step_name}.completed_at"] = firestore.SERVER_TIMESTAMP
            updates[f"steps.{step_name}.data"] = data
            
            # Move to next step
            current_idx = self.ALL_STEPS.index(step_name)
            if current_idx < len(self.ALL_STEPS) - 1:
                updates["current_step"] = self.ALL_STEPS[current_idx + 1]
            else:
                updates["overall_status"] = self.OVERALL_STATUS_COMPLETED
        
        doc_ref.update(updates)
    
    def get_process(self, request_id: str) -> dict | None:
        """Retrieve process state."""
        doc = self.db.collection(self.collection_name).document(request_id).get()
        return doc.to_dict() if doc.exists else None
```

**📁 Reference:** `python/agents/small-business-loan-agent/small_business_loan_agent/shared_libraries/firestore_utils/state_service.py`

---

### 10.3 Callback-based State Persistence

```python
from google.adk.agents.callback_context import CallbackContext

# Map agent names to their output keys
AGENT_OUTPUT_KEY_MAP = {
    "DocumentExtractionAgent": "extracted_documents",
    "UnderwritingAgent": "underwriting_result",
    "PricingAgent": "pricing_result",
    "LoanDecisionAgent": "loan_decision",
}

async def after_agent_callback_with_state_logging(
    callback_context: CallbackContext
) -> None:
    """Persist agent results to Firestore after each agent run."""
    try:
        request_id = callback_context.state.get("request_id")
        agent_name = callback_context.agent_name
        
        if not request_id:
            return
        
        # Get agent output from state
        output_key = AGENT_OUTPUT_KEY_MAP.get(agent_name)
        output_data = callback_context.state.get(output_key) if output_key else None
        
        # Persist to Firestore
        state_service = ProcessStateService()
        state_service.update_step(
            request_id=request_id,
            step_name=agent_name,
            status=ProcessStateService.STATUS_COMPLETED,
            data=output_data,
        )
        
    except Exception as e:
        print(f"Error persisting state: {e}")

# Attach to agent
agent = Agent(
    after_agent_callback=after_agent_callback_with_state_logging,
    # ...
)
```

---

### 10.4 BigQuery Agent Analytics Plugin

```python
from google.adk.plugins import BigQueryAgentAnalyticsPlugin
from google.adk.apps.app import App

# Initialize plugin
bq_plugin = BigQueryAgentAnalyticsPlugin(
    project_id="my-project",
    dataset_id="agent_analytics",
    table_id="agent_logs",
    location="us-central1",
)

# Create app with plugin
app = App(
    name="my_agent",
    root_agent=root_agent,
    plugins=[bq_plugin],
)
```

**📁 Reference:** `python/agents/agent-observability-bq/agent_observability_bq/agent.py`

---

## 🔗 Level 11: Agent-to-Agent (A2A) Protocol

### 11.1 Exposing an Agent via A2A

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent

# Create your agent
root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="currency_agent",
    description="Agent that helps with currency conversions",
    instruction="You convert currencies using the get_exchange_rate tool.",
    tools=[get_exchange_rate],
)

# Expose via A2A protocol
a2a_app = to_a2a(root_agent, port=10000)

# Run with: uvicorn agent:a2a_app --host 0.0.0.0 --port 10000
```

**What `to_a2a()` does:**
- Creates a FastAPI application
- Auto-generates agent card at `/.well-known/agent.json`
- Exposes A2A-compatible endpoints

**📁 Reference:** `python/agents/currency-agent/currency_agent/agent.py`

---

### 11.2 Calling Remote A2A Agents (Client)

```python
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    SendMessageRequest, MessageSendParams,
    GetTaskRequest, TaskQueryParams,
)
from uuid import uuid4

AGENT_URL = "http://localhost:10000"

async def call_remote_agent(query: str) -> str:
    """Call a remote A2A agent."""
    async with httpx.AsyncClient() as httpx_client:
        # Resolve agent card
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=AGENT_URL,
        )
        agent_card = await resolver.get_agent_card()
        
        # Create client
        client = A2AClient(
            httpx_client=httpx_client,
            agent_card=agent_card,
        )
        
        # Send message
        payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": query}],
                "messageId": uuid4().hex,
            }
        }
        
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**payload)
        )
        
        response = await client.send_message(request)
        return response.root.result

# Multi-turn conversation
async def multi_turn_conversation():
    """Maintain conversation context across turns."""
    # First turn
    response1 = await call_remote_agent("How much is 100 USD?")
    context_id = response1.context_id
    task_id = response1.id
    
    # Second turn (with context)
    payload = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "in EUR please"}],
            "messageId": uuid4().hex,
            "taskId": task_id,
            "contextId": context_id,
        }
    }
    # ... continue conversation
```

**📁 Reference:** `python/agents/currency-agent/currency_agent/test_client.py`

---

### 11.3 Using Remote Agent as Sub-Agent

```python
from google.adk.a2a.remote_a2a_agent import RemoteA2aAgent

# Create remote agent reference
currency_agent = RemoteA2aAgent(
    name="currency_agent",
    description="Remote agent for currency conversions",
    agent_card="http://localhost:10000/.well-known/agent.json"
)

# Use as sub-agent in your agent
root_agent = Agent(
    name="travel_assistant",
    sub_agents=[currency_agent],  # Can delegate to remote agent
    # ...
)

# Or wrap as AgentTool
from google.adk.tools import AgentTool

root_agent = Agent(
    tools=[AgentTool(agent=currency_agent)],
    # ...
)
```

---

## 🧠 Level 12: Vertex AI Memory Bank

### 12.1 Memory Bank Configuration

```python
from vertexai._genai.types import (
    ManagedTopicEnum,
    MemoryBankCustomizationConfig as CustomizationConfig,
    MemoryBankCustomizationConfigMemoryTopic as MemoryTopic,
    MemoryBankCustomizationConfigMemoryTopicManagedMemoryTopic as ManagedMemoryTopic,
    ReasoningEngineContextSpecMemoryBankConfig as MemoryBankConfig,
)

# Configure memory topics
memory_bank_config = MemoryBankConfig(
    customization_configs=[
        CustomizationConfig(
            memory_topics=[
                # User's personal information (name, relationships, hobbies)
                MemoryTopic(
                    managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.USER_PERSONAL_INFO,
                    ),
                ),
                # User's preferences (likes, dislikes, styles)
                MemoryTopic(
                    managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.USER_PREFERENCES,
                    ),
                ),
                # Things user explicitly asks to remember/forget
                MemoryTopic(
                    managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.EXPLICIT_INSTRUCTIONS,
                    ),
                ),
                # Key conversation milestones
                MemoryTopic(
                    managed_memory_topic=ManagedMemoryTopic(
                        managed_topic_enum=ManagedTopicEnum.KEY_CONVERSATION_DETAILS,
                    ),
                ),
            ],
        ),
    ],
)
```

**Available Managed Topics:**
| Topic | Description |
|-------|-------------|
| `USER_PERSONAL_INFO` | Names, relationships, hobbies, important dates |
| `USER_PREFERENCES` | Likes, dislikes, preferred styles |
| `KEY_CONVERSATION_DETAILS` | Milestones, task outcomes |
| `EXPLICIT_INSTRUCTIONS` | Things user asks agent to remember/forget |

**📁 Reference:** `python/agents/memory-bank/app/app_utils/memory_config.py`

---

### 12.2 Memory Tools

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.memory import LoadMemoryTool
from google.adk.agents import Agent

# PreloadMemoryTool - Auto-inject memories at turn start
root_agent = Agent(
    name="assistant",
    instruction="You remember user preferences from previous conversations.",
    tools=[
        PreloadMemoryTool(),  # Memories injected into system prompt automatically
    ],
)

# LoadMemoryTool - On-demand retrieval (model decides when)
root_agent = Agent(
    name="assistant", 
    tools=[
        LoadMemoryTool(),  # Model calls explicitly when needed
    ],
)
```

**Difference:**
- `PreloadMemoryTool`: Always retrieves relevant memories, injects into context
- `LoadMemoryTool`: Model decides when to retrieve memories

---

### 12.3 Storing Memories

```python
from google.adk.agents.callback_context import CallbackContext

async def generate_memories_callback(callback_context: CallbackContext):
    """Store session events as memories after each turn."""
    await callback_context.add_session_to_memory()
    return None

# Attach to agent
root_agent = Agent(
    name="memory_agent",
    tools=[PreloadMemoryTool()],
    after_agent_callback=generate_memories_callback,
)
```

---

### 12.4 Deployment with Memory Bank

```python
from google.adk.apps import get_fast_api_app

# For Cloud Run / FastAPI deployment
app = get_fast_api_app(
    agents_dir=".",
    session_service_uri="agentengine://projects/my-project/locations/us-central1/reasoningEngines/123",
    memory_service_uri="agentengine://projects/my-project/locations/us-central1/reasoningEngines/123",
)

# For Agent Engine deployment
from vertexai.preview.reasoning_engines import ReasoningEngineContextSpec

context_spec = ReasoningEngineContextSpec(
    memory_bank_config=memory_bank_config,
)

config = AgentEngineConfig(
    context_spec=context_spec,
    # ...
)
```

**📁 Reference:** `python/agents/memory-bank/app/agent.py`

---

## 🔌 Level 13: MCP (Model Context Protocol) Servers

### 13.1 Creating an MCP Server (FastMCP)

```python
# mcp_server.py
from fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("my-mcp-server")

@mcp.tool()
def get_exchange_rate(
    currency_from: str = "USD",
    currency_to: str = "EUR",
    currency_date: str = "latest",
):
    """Get current exchange rate between currencies.
    
    Args:
        currency_from: Source currency code (e.g., "USD")
        currency_to: Target currency code (e.g., "EUR")
        currency_date: Date for rate or "latest"
    
    Returns:
        Exchange rate data dictionary
    """
    response = httpx.get(
        f"https://api.frankfurter.app/{currency_date}",
        params={"from": currency_from, "to": currency_to},
    )
    response.raise_for_status()
    return response.json()

@mcp.tool()
async def search_products(query: str, limit: int = 10):
    """Search product catalog.
    
    Args:
        query: Search query string
        limit: Maximum results to return
    
    Returns:
        List of matching products
    """
    # Async implementation
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.example.com/products",
            params={"q": query, "limit": limit}
        )
        return response.json()

if __name__ == "__main__":
    import asyncio
    asyncio.run(
        mcp.run_async(
            transport="http",      # or "sse"
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8080")),
        )
    )
```

**Run:** `python mcp_server.py`

**📁 Reference:** `python/agents/currency-agent/mcp-server/server.py`

---

### 13.2 Connecting Agents to MCP Servers

**HTTP Connection:**
```python
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

root_agent = LlmAgent(
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="http://localhost:8080/mcp"
            )
        )
    ],
)
```

**SSE Connection (with timeout):**
```python
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

MCPToolset(
    connection_params=SseConnectionParams(
        url="http://localhost:8080/sse",
        timeout=30,
        sse_read_timeout=600,
    )
)
```

**Stdio Connection (local subprocess):**
```python
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["@example/mcp-server"],
            env={"API_KEY": os.getenv("API_KEY")},
        ),
    ),
)
```

---

### 13.3 MCP with Authentication

```python
# Bearer token auth
MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://api.example.com/mcp",
        headers={
            "Authorization": f"Bearer {os.getenv('API_TOKEN')}"
        },
    )
)

# Google Cloud ID token (for authenticated Cloud Run)
import subprocess

token = subprocess.check_output(
    ["gcloud", "auth", "print-identity-token"],
    text=True
).strip()

MCPToolset(
    connection_params=SseConnectionParams(
        url="https://my-mcp-server.run.app/sse",
        headers={"Authorization": f"Bearer {token}"},
    )
)
```

---

### 13.4 Tool Filtering

```python
# Only expose specific tools from MCP server
MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url="..."),
    tool_filter=[
        "search_products",
        "get_product_details",
        # Excludes: "delete_product", "update_inventory", etc.
    ],
)
```

---

### 13.5 Graceful Error Handling

```python
from google.adk.tools.mcp_tool import McpToolset

class SafeMCPToolset(McpToolset):
    """MCP toolset that gracefully handles connection failures."""
    
    async def get_tools(self, *args, **kwargs):
        try:
            return await super().get_tools(*args, **kwargs)
        except Exception as e:
            print(f"MCP server unavailable: {e}")
            print("Continuing without MCP tools.")
            return []  # Agent continues without these tools

# Use SafeMCPToolset instead of MCPToolset
root_agent = Agent(
    tools=[SafeMCPToolset(connection_params=...)],
)
```

**📁 Reference:** `python/agents/policy-as-code/policy_as_code_agent/mcp.py`

---

## 📋 Updated Cheat Sheet

### Evaluation
```python
# Arize tracing
instrument_adk_with_arize()

# Phoenix LLM evaluation
llm_classify(data=df, model=phoenix_model, template=template, rails=rails)

# Arize experiment
arize_client.run_experiment(dataset_id=..., task=..., evaluators=[...])
```

### Session Storage
```python
# Database URI
session_service_uri="sqlite:///./sessions.db"
session_service_uri="postgresql://user:pass@host:5432/db"

# Vertex AI managed
VertexAiSessionService(project_id, location)

# Firestore state
ProcessStateService().update_step(request_id, step_name, status, data)
```

### A2A Protocol
```python
# Expose agent
a2a_app = to_a2a(root_agent, port=10000)

# Call remote agent
client = A2AClient(httpx_client=..., agent_card=...)
await client.send_message(request)

# Use as sub-agent
RemoteA2aAgent(name=..., agent_card="http://host/.well-known/agent.json")
```

### Memory Bank
```python
# Configure
MemoryBankConfig(customization_configs=[CustomizationConfig(memory_topics=[...])])

# Tools
PreloadMemoryTool()  # Auto-inject
LoadMemoryTool()     # On-demand

# Store
await callback_context.add_session_to_memory()
```

### MCP
```python
# Create server
@mcp.tool()
def my_tool(...): ...

# Connect
MCPToolset(connection_params=StreamableHTTPConnectionParams(url=...))
MCPToolset(connection_params=SseConnectionParams(url=..., headers=...))
MCPToolset(connection_params=StdioConnectionParams(server_params=...))
```

---

> **Last Updated:** April 2026  
> **Based on:** ADK Samples Repository (71 agents analyzed)
