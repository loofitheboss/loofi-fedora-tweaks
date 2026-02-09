# Roadmap v18.0 "Sentinel" — Autonomous System Agents

## Vision

v18.0 transforms Loofi Fedora Tweaks from a reactive system management tool into a **proactive, agent-driven platform**. Users define goals in natural language, and Sentinel agents autonomously monitor, maintain, and optimize the system — with safety guardrails and full transparency.

## Core Architecture

### Agent Framework (`utils/agents.py`)
- **AgentConfig**: Declarative agent definition (type, triggers, actions, settings)
- **AgentState**: Runtime state with history, rate limiting, status tracking
- **AgentRegistry**: Singleton for agent CRUD, persistence, and querying
- **Built-in Agents**: 5 pre-configured agents covering monitoring, security, updates, cleanup, and performance

### Agent Runner (`utils/agent_runner.py`)
- **AgentExecutor**: Maps operations to real system checks/commands
  - 14 built-in operations: CPU, memory, disk, temperature, ports, logins, firewall, DNF updates, Flatpak updates, cache cleanup, journal vacuum, temp files, workload detection, tuning
- **AgentScheduler**: Background thread-based scheduling with interval triggers
- **Safety features**: rate limiting, dry-run mode, severity gating (CRITICAL actions require manual approval)

### Agent Planner (`utils/agent_planner.py`)
- Natural language goal → agent configuration pipeline
- Template matching for 5 common goals (health, security, updates, cleanup, performance)
- Ollama LLM fallback for custom goal interpretation
- Operation catalog with severity metadata

### Agents Tab (`ui/agents_tab.py`)
- **Dashboard**: Live summary cards (total, enabled, running, errors, total runs), scheduler controls, recent activity
- **My Agents**: Table view with enable/disable/run controls per agent
- **Create Agent**: Goal input with template buttons, AI-powered plan generation, dry-run/rate-limit configuration
- **Activity Log**: Timestamped history of all agent actions across all agents

### CLI Commands
```
loofi agent list              # Show all agents
loofi agent status            # Summary statistics
loofi agent enable <id>       # Enable an agent
loofi agent disable <id>      # Disable an agent
loofi agent run <id>          # Run an agent immediately
loofi agent create --goal "…" # Create agent from natural language goal
loofi agent remove <id>       # Remove a custom agent
loofi agent logs [id]         # Show activity logs
loofi agent templates         # Show available goal templates
```

## Built-in Agent Types

| Agent | Type | Default Interval | Operations |
|-------|------|------------------|------------|
| System Monitor | `system_monitor` | 60s | CPU, memory, disk, temperature |
| Security Guard | `security_guard` | 5min | Port scan, failed logins, firewall |
| Update Watcher | `update_watcher` | 1hr | DNF updates, Flatpak updates |
| Cleanup Bot | `cleanup_bot` | 24hr | DNF cache, journal, temp files |
| Performance Optimizer | `performance_optimizer` | 2min | Workload detection, tuning |

## Safety Design

1. **Dry-run by default**: New agents start in dry-run mode — they log what they would do without actually doing it
2. **Rate limiting**: Configurable max actions per hour (default: 10)
3. **Severity gating**: 
   - `INFO`/`LOW` — execute automatically
   - `MEDIUM` — execute in normal mode, confirm in strict mode
   - `HIGH` — always prompt for confirmation
   - `CRITICAL` — never execute automatically (requires manual trigger)
4. **No privilege escalation**: Agents read system state but don't `pkexec` — privileged actions redirect to the appropriate GUI tab
5. **History bounded**: Agent history capped at 100 entries per agent

## Goal Templates

| Goal | Maps To | Confidence |
|------|---------|------------|
| "Keep my system healthy" | Health Guardian (monitoring) | High |
| "Watch for security threats" | Security Sentinel | High |
| "Notify me about updates" | Update Notifier | High |
| "Automatically clean up my system" | Cleanup Automator | High |
| "Optimize system performance" | Performance Tuner | High |

## Future Enhancements (v18.x)

- [ ] Agent-to-agent communication (e.g., cleanup bot triggered by disk monitor alert)
- [ ] Webhook/notification integration (Telegram, email, desktop notifications)
- [ ] CRON-style scheduling (not just intervals)
- [ ] Agent export/import (share agent configs)
- [ ] Agent marketplace (community-shared agent templates)
- [ ] Event-driven triggers from SystemPulse integration
- [ ] AI-powered anomaly detection (learning from history)
- [ ] Agent conflict resolution (prevent competing agents)

## Files Added/Modified

### New Files
- `loofi-fedora-tweaks/utils/agents.py` — Agent framework and registry
- `loofi-fedora-tweaks/utils/agent_runner.py` — Executor and scheduler
- `loofi-fedora-tweaks/utils/agent_planner.py` — AI-powered planning
- `loofi-fedora-tweaks/ui/agents_tab.py` — GUI tab
- `tests/test_agents.py` — Comprehensive test suite
- `docs/ROADMAP_V18.md` — This document

### Modified Files
- `loofi-fedora-tweaks/version.py` — v18.0.0 "Sentinel"
- `loofi-fedora-tweaks/ui/main_window.py` — Added Agents tab (26 total tabs)
- `loofi-fedora-tweaks/cli/main.py` — Added `agent` subcommand
- `CHANGELOG.md` — v18.0.0 entry
- `release_notes.md` — v18.0.0 release notes