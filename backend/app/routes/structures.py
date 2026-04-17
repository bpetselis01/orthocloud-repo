from fastapi import APIRouter

router = APIRouter()


@router.get("/structures")
def get_structures():
    return {"status": "not implemented"}
