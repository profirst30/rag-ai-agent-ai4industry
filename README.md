# LiteLLM + Ollama Tool-Calling Agent (Branch: hiba)

## Overview
This branch contains my final implementation of a local AI agent using **Ollama** with **LiteLLM** as an OpenAI-compatible proxy, focusing on **tool-calling** instead of manual routing logic.

No paid OpenAI API is used.

---

## Files
- `mainn.ipynb`  
  Main notebook containing the agent logic, tool definition, and execution flow.

- `litellm_config.yaml`  
  LiteLLM configuration mapping the local Ollama model.

- `README.md`  
  Project documentation.

---

## Architecture
```
User Query
   ↓
Agent (OpenAI-compatible client)
   ↓
Tool Call (retrieve_from_index)
   ↓
Local Resources / Index
   ↓
Tool Output
   ↓
Final Answer
```

---

## Tech Stack
- Ollama (local LLM runtime)
- LiteLLM (OpenAI-compatible proxy)
- OpenAI Python SDK
- Jupyter Notebook

---

## Setup

### 1. Start Ollama
```bash
ollama serve
```

### 2. Start LiteLLM
```bash
python -m litellm --config litellm_config.yaml --port 4000
```

### 3. Run the Notebook
Open and execute:
```
mainn.ipynb
```

Ensure the client configuration uses:
```python
base_url = "http://localhost:4000/v1"
MODEL = "<model_name_from_litellm_config>"
```

---

## Tool
### `retrieve_from_index`
- Retrieves information from local indexed resources
- Includes a safety kill-switch to avoid hallucinations when no data is found

---
