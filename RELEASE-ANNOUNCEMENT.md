# Loofi Fedora Tweaks v20.0.1 "Synapse" Release Announcement

## TL;DR

Loofi Fedora Tweaks v20.0.1 "Synapse" is now available! This major release adds **remote system management** via a headless web API, an **EventBus "Hive Mind"** for autonomous agents, and comprehensive security testing.

**Install now:** `sudo dnf copr enable loofitheboss/loofi-fedora-tweaks && sudo dnf install loofi-fedora-tweaks`

**GitHub Release:** https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v20.0.1

---

## What's New in v20.0.1 "Synapse"

### 🌐 Loofi Web API (Remote Management)

Manage your Fedora system remotely through a secure REST API:

```bash
# Start headless web server
loofi-fedora-tweaks --web

# Access from anywhere
curl https://loofi.example.com/api/health
# {"status": "ok", "version": "20.0.1", "codename": "Synapse"}
```

**Key Features:**
- **JWT Authentication** with bcrypt-hashed API keys
- **Mandatory Preview Mode**: All actions preview first, real execution is opt-in
- **System Monitoring**: CPU, memory, uptime, package manager detection
- **Agent Management**: View and control autonomous agents remotely
- **RESTful Endpoints**: `/api/health`, `/api/info`, `/api/agents`, `/api/execute`

### 🧠 EventBus "Hive Mind"

Autonomous agents communicate through a thread-safe pub/sub system:
- Storage cleanup agent triggers when disk space is low
- Agents subscribe to system events and coordinate actions
- Async callback execution prevents blocking
- Foundation for future AI-driven system management

### 🛡️ Security & Testing

**66 new tests** ensuring production-ready security:
- 28 API security tests (authentication, authorization, input validation)
- 18 EventBus tests (concurrency, thread safety, error handling)
- 10 agent integration tests (event subscriptions, action execution)
- 10 agent implementation tests (cleanup agent, notification agent)

### 📦 Installation & Usage

**Fedora 40/41 (via COPR):**
```bash
sudo dnf copr enable loofitheboss/loofi-fedora-tweaks
sudo dnf install loofi-fedora-tweaks
```

**GUI Mode (default):**
```bash
loofi-fedora-tweaks
```

**Headless Web API:**
```bash
loofi-fedora-tweaks --web
```

**Generate API Key:**
```bash
curl -X POST http://localhost:8000/api/key
# {"api_key": "loofi_<random_secure_key>"}
```

**Get JWT Token:**
```bash
curl -X POST http://localhost:8000/api/token -d "api_key=loofi_..."
# {"access_token": "eyJ...", "token_type": "bearer"}
```

**Execute System Action (with preview):**
```bash
curl -X POST http://localhost:8000/api/execute \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"command": "dnf", "args": ["clean", "all"], "preview": true}'
```

### 🚀 Use Cases

1. **Homelab Management**: Control multiple Fedora systems from a central dashboard
2. **CI/CD Integration**: Automate system tweaks in deployment pipelines
3. **Remote Administration**: Manage headless servers without SSH
4. **Agent Automation**: Let autonomous agents handle routine maintenance

### 📊 Architecture Highlights

- **FastAPI** for modern async Python REST API
- **Uvicorn** for production-grade ASGI server
- **ThreadPoolExecutor** for async event processing
- **Singleton patterns** for EventBus and AgentRegistry
- **Pydantic models** for request/response validation
- **python-jose** for JWT token management
- **bcrypt** for secure password hashing

### 🔗 Links

- **GitHub Release**: https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v20.0.1
- **Full Changelog**: https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/CHANGELOG.md
- **Documentation**: https://github.com/loofitheboss/loofi-fedora-tweaks#readme
- **Report Issues**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues

### 🎯 What's Next (v21.0.0 Roadmap)

- Web dashboard UI for remote management
- Real-time WebSocket notifications
- Multi-agent orchestration patterns
- AI-powered system optimization

### 💬 Feedback Welcome!

This is a **major architectural shift** toward autonomous system management. We'd love your feedback on:
- API design and ergonomics
- Security model and authentication flow
- Agent use cases and feature requests
- Integration with existing tools (Ansible, Terraform, etc.)

Try it out and let us know what you think!

---

**Credits:**
- Developed with assistance from Claude Code (Anthropic)
- Built for the Fedora Linux community
- Open source under MIT License

**Maintainer:** Loofi ([@loofitheboss](https://github.com/loofitheboss))
