from fastapi import APIRouter

router = APIRouter(tags=["System"])

@router.get("/")
def read_root():
    return {"status": "ok", "service": "Consigliere API"}
