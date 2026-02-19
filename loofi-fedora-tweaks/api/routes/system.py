"""System information API routes.

Security:
- /health is unauthenticated but does NOT expose version info.
- /info and /agents require Bearer JWT authentication.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from utils.agents import AgentRegistry
from utils.monitor import SystemMonitor
from utils.auth import AuthManager
from services.system import SystemManager

router = APIRouter()


class HealthResponse(BaseModel):
    """Health response payload — no version info for unauthenticated callers."""

    status: str


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Basic health check endpoint (unauthenticated, no version leak)."""
    return HealthResponse(status="ok")


@router.get("/info")
def get_info(
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Return system info and health metrics (authenticated)."""
    from version import __version__, __version_codename__

    health = SystemMonitor.get_system_health()
    return {
        "version": __version__,
        "codename": __version_codename__,
        "system_type": "Atomic" if SystemManager.is_atomic() else "Traditional",
        "package_manager": SystemManager.get_package_manager(),
        "health": {
            "hostname": health.hostname,
            "uptime": health.uptime,
            "memory": {
                "used": health.memory.used_human if health.memory else None,
                "total": health.memory.total_human if health.memory else None,
                "percent": health.memory.percent_used if health.memory else None,
                "status": health.memory_status,
            },
            "cpu": {
                "load_1min": health.cpu.load_1min if health.cpu else None,
                "load_5min": health.cpu.load_5min if health.cpu else None,
                "load_15min": health.cpu.load_15min if health.cpu else None,
                "cores": health.cpu.core_count if health.cpu else None,
                "load_percent": health.cpu.load_percent if health.cpu else None,
                "status": health.cpu_status,
            },
        },
    }


@router.get("/agents")
def get_agents(
    _auth: str = Depends(AuthManager.verify_bearer_token),
):
    """Return agent configs and runtime states (authenticated)."""
    registry = AgentRegistry.instance()
    agents = registry.list_agents()
    return {
        "agents": [a.to_dict() for a in agents],
        "states": [registry.get_state(a.agent_id).to_dict() for a in agents],
        "summary": registry.get_agent_summary(),
    }
