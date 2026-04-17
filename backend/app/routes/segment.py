from fastapi import APIRouter

router = APIRouter()


@router.post("/segment")
def post_segment():
    return {"status": "not implemented"}
