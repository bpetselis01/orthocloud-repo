# Step 1: Import APIRouter — lets this file define its own routes independently
# The router is registered in main.py; adding endpoints here requires no changes there
from fastapi import APIRouter

# Step 2: Create the router instance for structure-related endpoints
router = APIRouter()


# Step 3: GET /structures — stub returning a not-implemented marker
# In Step 2 this will return the list of anatomy labels produced by TotalSegmentator
@router.get("/structures")
def get_structures():
    return {"status": "not implemented"}
