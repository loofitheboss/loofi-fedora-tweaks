# AI & Voice Skills

## Local LLM Integration (Ollama)

- **Model management** — List, pull, delete Ollama models
- **Model inference** — Send prompts to local LLM for responses
- **System analysis** — Use LLM to analyze system logs and suggest fixes
- **Natural language commands** — Convert natural language to system operations

**Modules:** `utils/ai.py`
**UI:** AI Enhanced Tab
**CLI:** `ai-models`

## Voice Commands

- **Speech recognition** — Convert voice input to text commands
- **Voice activation** — Trigger Loofi operations via voice
- **Text-to-speech** — Speak operation results and notifications

**Modules:** `utils/voice.py`
**UI:** AI Enhanced Tab

## Context RAG

- **Context management** — Retrieval-augmented generation for relevant context
- **Knowledge base** — Build searchable index of system state and documentation
- **Contextual suggestions** — Provide context-aware recommendations

**Modules:** `utils/context_rag.py`

## Intelligent Arbitration

- **Decision making** — AI-assisted decision support for complex operations
- **Conflict resolution** — Resolve conflicting configuration changes
- **Risk assessment** — Evaluate risk of proposed system changes

**Modules:** `utils/arbitrator.py`
