# Automation & Agents Skills

## Task Scheduling
- **Time-based scheduling** — Schedule tasks daily, weekly, or at specific times
- **On-boot tasks** — Run tasks automatically at system startup
- **Power-state triggers** — Trigger tasks on AC/battery switch
- **Cron integration** — Manage cron jobs through the UI

**Modules:** `utils/scheduler.py`
**UI:** Automation Tab

## Autonomous Agents
- **Agent runners** — Background task execution with progress tracking
- **Agent scheduling** — Schedule autonomous agent runs
- **Agent planning** — AI-assisted task planning and sequencing
- **Agent monitoring** — Track agent status and results

**Modules:** `utils/agent_runner.py`, `utils/agent_scheduler.py`
**UI:** Agents Tab
**CLI:** `agent`

## Event Bus
- **Publish/Subscribe** — Application-wide event notification system
- **Event filtering** — Subscribe to specific event types
- **Cross-module communication** — Decouple modules via events

**Modules:** `utils/event_bus.py`

## Batch Operations
- **Bulk execution** — Run multiple operations in sequence or parallel
- **Progress tracking** — Monitor batch operation progress
- **Error handling** — Continue or abort on individual operation failure

**Modules:** `utils/batch_ops.py`

## Daemon Mode
- **Background scheduler** — Run scheduled tasks as a system daemon
- **Service integration** — Systemd service file for daemon management
- **Persistent tasks** — Tasks survive application restarts

**Modules:** `utils/daemon.py`
**Service:** `loofi-fedora-tweaks.service`
**Entry:** `main.py --daemon`

## Workflow Automation
- **Task runners** — Define and execute multi-step workflows
- **Conditional execution** — Branch workflows based on system state
- **Notification on completion** — Alert when workflows finish

**UI:** Automation Tab
