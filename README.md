# 🎯 ADK Master Example

> **One comprehensive example that demonstrates ALL Google ADK features**

This is a single, runnable Python project that covers every concept from the 71+ agents in the ADK samples repository. Use this to learn ADK from scratch or as a reference implementation.

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 2. Install Dependencies

```bash
cd python/agents/adk-master-example
pip install -r requirements.txt
```

### 3. Run the Agent

```bash
# Interactive chat mode
python run.py

# Or use ADK CLI
adk run agent:app

# Or use ADK web interface (recommended for visual debugging)
adk web agent:app
```

---

## 📚 Features Covered

### Level 1: Foundations
| Feature | Location in Code | Description |
|---------|------------------|-------------|
| Basic `Agent` | `root_agent` | Main agent with tools and callbacks |
| `LlmAgent` | `researcher_agent`, `analyzer_agent` | Agents with specific configurations |
| Model Configuration | `creative_writer_agent` | Temperature control (0.9 vs 0.2) |
| Prompt Templates | `ROOT_INSTRUCTION` | Using `{{state_key}}` for dynamic prompts |

### Level 2: Multi-Agent Orchestration
| Feature | Location in Code | Description |
|---------|------------------|-------------|
| `sub_agents` | Commented in `root_agent` | Direct agent delegation |
| `AgentTool` | `root_agent.tools` | Wrap agents as callable tools |

### Level 3: Workflow Patterns
| Feature | Location in Code | Description |
|---------|------------------|-------------|
| `SequentialAgent` | `research_pipeline` | Run agents in order |
| `ParallelAgent` | `parallel_writers` | Run agents concurrently |
| `LoopAgent` | `refinement_loop` | Iterate until condition met |
| Custom `BaseAgent` | `ValidationCheckerAgent` | Custom validation with `EventActions(escalate=True)` |

### Level 4: Tools
| Feature | Location in Code | Description |
|---------|------------------|-------------|
| `FunctionTool` | `get_current_time`, `calculate_expression` | Wrap Python functions |
| `ToolContext` | All custom tools | Access session state in tools |
| `google_search` | `researcher_agent` | Built-in web search |
| `AgentTool` | `root_agent.tools` | Use agents as tools |

### Level 5: Callbacks
| Callback | Function | Use Case |
|----------|----------|----------|
| `before_agent_callback` | `before_agent_callback()` | Input validation, state init |
| `after_agent_callback` | `after_agent_callback()` | Output validation, logging |
| `before_tool_callback` | `before_tool_callback()` | Tool gating, argument validation |
| `after_tool_callback` | `after_tool_callback()` | Side effects, response transform |
| `before_model_callback` | `before_model_callback()` | Rate limiting |

### Level 6: State Management
| Feature | Location in Code | Description |
|---------|------------------|-------------|
| `output_key` | All sub-agents | Store agent output in state |
| `ToolContext.state` | All tools | Read/write session state |
| Template Variables | Agent instructions | `{{research_output}}` syntax |
| State Tracking | `get_session_summary` | View full session state |

### Level 8: Production Patterns
| Feature | Location in Code | Description |
|---------|------------------|-------------|
| Dataclass Config | `AgentConfig` | Centralized typed configuration |
| Rate Limiting | `before_model_callback` | Request throttling |
| Structured Output | `TaskPlan`, `ResearchReport` | Pydantic models with `output_schema` |
| Error Handling | `calculate_expression` | Input validation and safe execution |

---

## 🗂️ File Structure

```
adk-master-example/
├── agent.py          # Core agent (Levels 1-8) - Start here!
├── agent_advanced.py # Advanced patterns (Levels 9-13) - Production features
├── run.py            # Simple runner script
├── requirements.txt  # Dependencies (core + optional advanced)
├── __init__.py       # Package init
├── .env.example      # Environment template (all options)
└── README.md         # This file
```

## 📚 Two Learning Files

### 1. `agent.py` - Core Concepts (Levels 1-8)
```bash
python run.py  # or: python agent.py
```
Covers:
- Basic Agent/LlmAgent structure
- Tools with ToolContext
- All 5 callback types
- SequentialAgent, ParallelAgent, LoopAgent
- Custom BaseAgent validation
- State management with output_key
- Structured output (Pydantic)

### 2. `agent_advanced.py` - Production Patterns (Levels 9-13)
```bash
python agent_advanced.py
```
Covers:
- **Arize/Phoenix** observability and LLM evaluation
- **Firestore** session and state persistence
- **A2A Protocol** for inter-agent communication
- **Memory Bank** for long-term memory
- **MCP Servers** for external tools

---

## 💬 Example Interactions

### Basic Tools
```
You: What time is it?
Assistant: [Calls get_current_time tool, shows state tracking]

You: Calculate 15 * 7 + 23
Assistant: [Calls calculate_expression, result: 128]

You: Store a note titled "Meeting Notes" with content "Discuss Q3 goals"
Assistant: [Stores note in session state]

You: Show my notes
Assistant: [Retrieves all notes from state]
```

### Research & Analysis (AgentTool)
```
You: Research the latest developments in quantum computing
Assistant: [Delegates to researcher_agent which uses google_search]
         [Returns summarized findings with sources]

You: Research and analyze the impact of AI on healthcare
Assistant: [Runs research_pipeline: researcher_agent → analyzer_agent]
         [Returns research findings + analysis with recommendations]
```

### Content Generation (Workflows)
```
You: Generate content about sustainable energy
Assistant: [Runs content_generation_workflow]
         [ParallelAgent: creative_writer + focused_writer run simultaneously]
         [SequentialAgent: critic_agent evaluates and selects best]
         [Returns final polished content]
```

### Task Planning (Loop with Validation)
```
You: Create a plan for launching a new product
Assistant: [Runs refinement_loop with planner_agent]
         [ValidationCheckerAgent checks if plan is complete]
         [Loops until valid TaskPlan is generated]
         [Returns structured plan with steps and complexity]
```

### Session State
```
You: state
Assistant: [Shows full session state summary]
         - session_start, message_count
         - tool_usage statistics
         - calculation_history
         - user_notes
         - successful_tool_calls
```

---

## 🔧 Customization

### Change Models
```python
# In agent.py, modify AgentConfig
@dataclass
class AgentConfig:
    main_model: str = "gemini-2.5-pro"  # Upgrade to Pro
    worker_model: str = "gemini-2.5-flash"
    temperature: float = 0.5  # Lower for more consistency
```

### Add New Tools
```python
def my_custom_tool(param1: str, tool_context: ToolContext) -> str:
    """My custom tool description."""
    # Access state
    value = tool_context.state.get("key")
    
    # Update state
    tool_context.state["new_key"] = "new_value"
    
    return "Result"

# Add to root_agent
tools=[
    FunctionTool(my_custom_tool),
    # ... existing tools
]
```

### Add New Sub-Agent
```python
my_expert_agent = LlmAgent(
    name="my_expert",
    model=config.worker_model,
    instruction="You are an expert in X...",
    tools=[google_search],
    output_key="expert_output",
)

# Use as AgentTool
tools=[AgentTool(agent=my_expert_agent)]

# Or as sub_agent
sub_agents=[my_expert_agent]
```

### Disable Debug Logging
```python
# In agent.py
config = AgentConfig(debug_mode=False)
```

---

## 🐛 Debugging

### View Callback Logs
The agent prints callback events when `debug_mode=True`:
```
🔵 [BEFORE_AGENT] Agent starting...
  🔧 [BEFORE_TOOL] Tool: get_current_time, Args: {}
  ✅ [AFTER_TOOL] Tool: get_current_time completed.
  🤖 [BEFORE_MODEL] LLM call initiated...
🟢 [AFTER_AGENT] Agent completed. Messages this session: 1
```

### View Session State
```
You: state
# Or programmatically:
You: Use get_session_summary to show me the current state
```

### Common Issues

**Authentication Error:**
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Rate Limit Hit:**
```
⏳ Rate limit reached. Sleeping 45.2s...
```
Adjust `requests_per_minute` in `AgentConfig`.

**Tool Not Found:**
Make sure tools are registered in `root_agent.tools=[]`.

---

## 📖 Learning Path

1. **Read `agent.py`** - Understand the structure
2. **Run `python run.py`** - Try the interactive chat
3. **Test each feature:**
   - Time/calculator tools → Basic tools
   - Notes → State persistence
   - Research → AgentTool pattern
   - Content generation → Workflow patterns
   - State command → Session management
4. **Modify and experiment:**
   - Add a new tool
   - Create a new sub-agent
   - Build a custom workflow
5. **Reference back to `ADK_AGENT_LEARNING_GUIDE.md`** for deeper explanations

---

## 🔗 Related Resources

- [ADK Learning Guide](../../ADK_AGENT_LEARNING_GUIDE.md) - Complete concept reference
- [ADK Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-builder/adk)
- [Other Agent Examples](../) - 71+ production examples

---

## 🔬 Advanced Features Setup

### Arize/Phoenix Observability (Level 9)

```bash
# Install
pip install openinference-instrumentation-google-adk arize-otel arize phoenix-evals

# Configure .env
ARIZE_SPACE_ID=your-space-id
ARIZE_API_KEY=your-api-key

# Run
python agent_advanced.py
```

All agent calls, tool executions, and LLM requests will be traced to Arize Phoenix.

### Firestore Persistence (Level 10)

```bash
# Install
pip install google-cloud-firestore

# Configure .env
ENABLE_FIRESTORE=true

# Run
python agent_advanced.py
```

Sessions and state will be persisted to Firestore.

### A2A Protocol (Level 11)

```bash
# Install
pip install a2a-sdk httpx

# Start as A2A server
uvicorn agent_advanced:a2a_app --port 10000

# Agent card available at:
# http://localhost:10000/.well-known/agent.json
```

Other agents can now discover and call your agent.

### Memory Bank (Level 12)

Requires Vertex AI Agent Engine deployment:

```bash
# Configure .env
ENABLE_MEMORY_BANK=true

# Deploy to Agent Engine first, then run with memory_service_uri
adk web . --memory_service_uri=agentengine://...
```

### MCP Server (Level 13)

```bash
# Install
pip install fastmcp

# Create server (see mcp_server_example.py)
# Then configure .env
MCP_SERVER_URL=http://localhost:8080/mcp

# Run agent
python agent_advanced.py
```

---

## 📖 Complete Learning Path

| Week | File | Concepts |
|------|------|----------|
| 1 | `agent.py` | Foundations, Tools, Callbacks |
| 2 | `agent.py` | Multi-agent, Workflows, State |
| 3 | `agent_advanced.py` | Arize, Firestore, Evaluation |
| 4 | `agent_advanced.py` | A2A, Memory Bank, MCP |

---

*Happy Learning! 🚀*
