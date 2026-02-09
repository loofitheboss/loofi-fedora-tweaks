"""System information API routes."""

from fastapi import APIRouter
from pydantic import BaseModel

from utils.agents import AgentRegistry
from utils.monitor import SystemMonitor
from utils.system import SystemManager
from version import __version__, __version_codename__

router = APIRouter()


class HealthResponse(BaseModel):
    """Health response payload."""

    status: str
    version: str
    codename: str


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Basic health check endpoint."""
    return HealthResponse(
        status="ok",
        version=__version__,
        codename=__version_codename__,
    )


@router.get("/info")
def get_info():
    """Return system info and health metrics."""
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
def get_agents():
    """Return agent configs and runtime states."""
    registry = AgentRegistry.instance()
    agents = registry.list_agents()
    return {
        "agents": [a.to_dict() for a in agents],
        "states": [registry.get_state(a.agent_id).to_dict() for a in agents],
        "summary": registry.get_agent_summary(),
    }