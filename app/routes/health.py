from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    """Lets you (or a monitoring script) check the server is up."""
    return {"status": "ok"}
