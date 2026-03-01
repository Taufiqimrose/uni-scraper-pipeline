from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Basic health check."""
    return {"status": "ok", "version": "0.1.0"}


@router.get("/ready")
async def readiness() -> dict[str, bool]:
    """Readiness check for all subsystems."""
    # TODO: Check database, browser pool, queue
    return {"database": True, "browser_pool": True, "queue": True}
