"""Shared FastAPI dependencies."""
from fastapi import HTTPException

from .services.runtime import Runtime, maybe_runtime, startup_error


def runtime_ready() -> Runtime:
    """Return the runtime, or a clear 503 while the server is still starting."""
    rt = maybe_runtime()
    if rt is None:
        from .services import runtime as rt_module

        if rt_module.startup_error:
            raise HTTPException(503, "The server failed to start. Check the server logs.")
        raise HTTPException(503, "The server is still starting up. Try again in a few seconds.")
    return rt
