# Release Notes — v18.0.0 "Sentinel"

## 🤖 Autonomous System Agents

v18.0 "Sentinel" introduces a complete **agent framework** that transforms Loofi Fedora Tweaks from a reactive tool into a proactive, agent-driven platform. Define your goals in plain English and let Sentinel agents autonomously monitor, maintain, and optimize your system.

---

### ✨ Headline Features

#### Agent Framework
- **5 built-in agents** ready to go: System Monitor, Security Guard, Update Watcher, Cleanup Bot, Performance Optimizer
- **AgentRegistry** with JSON persistence, enable/disable, and per-agent settings
- **AgentState** tracking with bounded history, rate limiting, and status monitoring

#### AI-Powered Agent Creation
- Describe what you want in natural language: _"Keep my system healthy"_
- **Template matching** for 5 common goals with high-confidence plans
- **Ollama LLM fallback** for interpreting custom goals into agent configs
- **14 built-in operations**: CPU, memory, disk, temperature, ports, logins, firewall, DNF/Flatpak updates, cache cleanup, journal vacuum, temp files, workload detection, tuning

#### Agent Execution Engine
- **AgentScheduler** with background thread-based interval scheduling
- **AgentExecutor** maps operations to real system checks
- **Dry-run mode** by default — new agents log what they _would_ do without acting
- **Rate limiting** — configurable max actions per hour (default: 10)
- **Severity gating** — CRITICAL actions are blocked from automation, requiring manual trigger

#### New Agents Tab (26th tab)
- **Dashboard**: Live stat cards, scheduler controls, recent activity feed
- **My Agents**: Table with enable/disable/run controls per agent
- **Create Agent**: Goal input with template buttons, AI plan generation, safety config
- **Activity Log**: Full history of all agent actions

#### CLI Agent Management
```bash
loofi agent list              # Show all agents
loofi agent status            # Summary statistics  
loofi agent create --goal "Keep my system healthy"
loofi agent enable <id>       # Activate an agent
loofi agent run <id>          # Run immediately
loofi agent logs              # View activity
loofi agent templates         # Browse goal templates
```

---

### 🛡️ Safety First

| Safety Feature | Description |
|---------------|-------------|
| Dry-run default | New agents start in simulation mode |
| Rate limiting | Max 10 actions/hour (configurable) |
| Severity gating | INFO/LOW auto, MEDIUM conditional, HIGH prompt, CRITICAL manual only |
| No privilege escalation | Agents read state but never `pkexec` |
| Bounded history | 100 entries max per agent |

---

### 📊 Built-in Agents

| Agent | Monitors | Default Interval |
|-------|----------|-----------------|
| 🏥 System Monitor | CPU, memory, disk, temperature | 60s |
| 🛡️ Security Guard | Open ports, failed logins, firewall | 5 min |
| 📦 Update Watcher | DNF packages, Flatpak apps | 1 hour |
| 🧹 Cleanup Bot | DNF cache, journal, temp files | 24 hours |
| ⚡ Performance Optimizer | Workload detection, tuning | 2 min |

---

### 🧪 Tests

- **60+ new tests** covering agent dataclasses, registry, executor, planner, scheduler, and CLI
- Full serialization/deserialization roundtrip tests
- Safety tests for dry-run, rate limiting, and severity gating

---

### 📁 New Files

| File | Purpose |
|------|---------|
| `utils/agents.py` | Agent framework, registry, built-in definitions |
| `utils/agent_runner.py` | Executor and background scheduler |
| `utils/agent_planner.py` | AI-powered natural language planning |
| `ui/agents_tab.py` | Agents management GUI |
| `tests/test_agents.py` | Comprehensive test suite |
| `docs/ROADMAP_V18.md` | Architecture and roadmap |

---

### 🔮 What's Next (v18.x)

- Agent-to-agent communication
- Webhook/notification integration (Telegram, email)
- CRON-style scheduling
- Agent export/import and marketplace
- SystemPulse event-driven triggers
- AI-powered anomaly detection