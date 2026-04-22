from .agent import router as agent_router
from .api_key import router as api_key_router
from .auth import router as auth_router
from .core import router as core_router
from .github import router as github_router
from .preset import router as preset_router
from .project import router as project_router
from .template import router as template_router
from .ws import router as ws_router

__all__ = [
    "agent_router",
    "api_key_router",
    "auth_router",
    "core_router",
    "github_router",
    "preset_router",
    "project_router",
    "template_router",
    "ws_router",
]
