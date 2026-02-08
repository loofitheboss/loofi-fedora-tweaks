"""
AI Lab Plugin - First-party plugin for local AI/LLM management.
Part of the Plugin Architecture Refactor for v12.0 "Sovereign Update".

Provides local AI model management, voice control, and RAG knowledge
indexing as an optional loadable plugin so users who don't need AI
features don't pay the import cost.
"""

import logging

from utils.plugin_base import LoofiPlugin, PluginInfo

logger = logging.getLogger("loofi.plugins.ai_lab")


class AILabPlugin(LoofiPlugin):
    """AI Lab plugin providing local AI model management and RAG indexing."""

    @property
    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="AI Lab",
            version="1.0.0",
            author="Loofi Team",
            description="Local AI models, voice control, and knowledge indexing",
            icon="\U0001f9e0",
        )

    def create_widget(self):
        """Lazily import and return the AITab widget.

        Uses __import__ to avoid importing PyQt6 at module load time,
        keeping the plugin lightweight when loaded only for CLI commands.
        """
        mod = __import__(
            "ui.ai_tab",
            fromlist=["AITab"],
        )
        return mod.AITab()

    def get_cli_commands(self) -> dict:
        """Return CLI commands provided by this plugin."""
        return {
            "ai-models": self._cmd_ai_models,
            "ai-status": self._cmd_ai_status,
            "rag-index": self._cmd_rag_index,
            "rag-search": self._cmd_rag_search,
        }

    def on_load(self) -> None:
        """Called when the plugin is loaded."""
        logger.info("AI Lab plugin loaded")

    def on_unload(self) -> None:
        """Called when the plugin is unloaded. Perform cleanup."""
        logger.info("AI Lab plugin unloaded")

    # ---- CLI command implementations ----

    @staticmethod
    def _cmd_ai_models() -> str:
        """List available and installed AI models."""
        from utils.ai import OllamaManager
        if not OllamaManager.is_installed():
            return "Ollama is not installed. Install with the AI Lab tab."
        models = OllamaManager.list_models()
        if not models:
            return "No models installed. Use 'ollama pull <model>' to download."
        lines = [f"  {m['name']} ({m['size']})" for m in models]
        return "Installed models:\n" + "\n".join(lines)

    @staticmethod
    def _cmd_ai_status() -> str:
        """Show AI capabilities and runtime status."""
        from utils.ai import OllamaManager, AIConfigManager
        installed = OllamaManager.is_installed()
        running = OllamaManager.is_running() if installed else False
        gpu_mem = AIConfigManager.get_gpu_memory()
        lines = [
            f"Ollama installed: {installed}",
            f"Ollama running: {running}",
            f"GPU memory: {gpu_mem['free_mb']} MB free / {gpu_mem['total_mb']} MB total",
        ]
        return "\n".join(lines)

    @staticmethod
    def _cmd_rag_index() -> str:
        """Trigger RAG knowledge indexing."""
        return "RAG indexing is not yet implemented. Coming in a future update."

    @staticmethod
    def _cmd_rag_search() -> str:
        """Search indexed knowledge base."""
        return "RAG search is not yet implemented. Coming in a future update."
