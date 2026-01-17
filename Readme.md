# Cognitive Memory Agent

A conversational AI agent with cognitive memory capabilities using Qwen as the LLM backbone.

## Architecture

```
[ USER INPUT ]
      │
      ▼
[ INPUT HANDLER ]  ← main.py
      │
      ▼
[ STM UPDATE ]     ← memory/stm.py
      │
      ▼
[ DECISION LAYER ] ← agent/decision_rules.py
      │
      ├───► (Use Tool?) ──► [ TOOL ]           ← agent/tools/
      │                    │
      │                    ▼
      │              [ TOOL RESULT ]
      │
      └───► (Need Memory?)
               │
               ▼
        [ MEMORY MANAGER ]  ← memory/memory_manager.py
               │
        ┌──────┴───────┐
        ▼              ▼
     [ STM ]         [ LTM ]  ← memory/ltm.py
        │              │
        └──────┬───────┘
               ▼
        [ CONTEXT BUILDER ]   ← context/prompt_generate.py
               │
               ▼
            [ LLM ]           ← core/llm.py (Qwen)
               │
               ▼
         [ OUTPUT HANDLER ]
               │
               ▼
           [ USER OUTPUT ]
```

## Project Structure

```
cognitive_memory/
├── core/
│   ├── __init__.py
│   ├── config.py      # Configuration management
│   └── llm.py         # Qwen LLM wrapper
├── memory/
│   ├── __init__.py
│   ├── stm.py         # Short-Term Memory
│   ├── ltm.py         # Long-Term Memory
│   └── memory_manager.py  # Memory coordination
├── agent/
│   ├── __init__.py
│   ├── decision_rules.py  # Decision layer
│   ├── tool_router.py     # Tool routing
│   └── tools/
│       ├── __init__.py
│       ├── base.py        # Tool base class
│       ├── calculator.py  # Math tool
│       └── datetime_tool.py  # DateTime & Memory tools
├── context/
│   ├── __init__.py
│   └── prompt_generate.py  # Context builder
├── data/                   # Memory storage (auto-created)
├── main.py                 # Main application
├── requirements.txt
└── README.md
```

## Features

### Memory System
- **STM (Short-Term Memory)**: Sliding window conversation history
- **LTM (Long-Term Memory)**: Persistent storage with semantic search
- **Automatic Consolidation**: Important info moves from STM to LTM

### Tools
- **Calculator**: Mathematical calculations
- **DateTime**: Date/time operations
- **Memory**: Explicit memory store/retrieve

### Decision Layer
- Analyzes user input to determine actions
- Supports tool usage, memory retrieval, and direct responses

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure model path in `core/config.py` or create a config JSON file

## Usage

### Basic Usage

```bash
python main.py
```

### With Configuration

```bash
python main.py --config config.json
```

### Debug Mode

```bash
python debug_model.py
```

### API Mode

```bash
python api/main.py
```

Or you can use uvicorn to run the API:

```bash
uvicorn api.main:app --reload
```

### API Documentation

```bash
http://localhost:8000/docs
```



### Commands

- Type your message to chat
- `clear` - Clear conversation history
- `clear all` - Clear all memory (STM + LTM)
- `stats` - Show memory statistics
- `quit` or `exit` - Exit the application

## Configuration

Create a `config.json` file:

```json
{
  "llm": {
    "model_path": "Local path to model",
    "max_new_tokens": 512,
    "temperature": 0.7,
    "device": "cuda" # or "cpu"
  },
  "memory": {
    "stm_max_turns": 10,
    "consolidate_after_turns": 5
  },
  "agent": {
    "enable_tools": true,
    "max_tool_iterations": 3
  },
  "debug": false
}
```

## Example Interactions

```
You: Hai, nama saya Jhon
Assistant: Hai Jhon! Senang berkenalan dengan kamu. Ada yang bisa saya bantu?

You: Berapa 25 * 48?
Assistant: [Using calculator] 25 × 48 = 1200

You: Ingat bahwa saya suka kopi
Assistant: Baik, saya sudah mencatat bahwa kamu suka kopi!

You: Apa yang kamu tahu tentang saya?
Assistant: Berdasarkan percakapan kita, saya tahu bahwa:
- Nama kamu adalah Jhon
- Kamu suka kopi
```
