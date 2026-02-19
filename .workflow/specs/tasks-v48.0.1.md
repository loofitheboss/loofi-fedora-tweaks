# Tasks — v48.0.1

## Contract

- [x] ID: T1 | Files: api/, utils/, tests/, .github/ | Dep: none | Agent: CodeGen | Description: Stabilization patch — API hardening, privilege hygiene, test coverage expansion, CI fixes
  Acceptance: CI fully green (14/14 jobs), 282 new tests, no sudo strings, API allowlist enforced
  Docs: CHANGELOG.md, SECURITY.md, ARCHITECTURE.md
  Tests: tests/test_auth.py, test_clipboard_sync.py, test_state_teleport.py, test_vfio.py, test_ai_models.py, test_disposable_vm.py, test_mesh_discovery.py, test_voice.py, test_arbitrator.py, test_agent_scheduler.py
