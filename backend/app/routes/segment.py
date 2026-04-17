# Step 1: Import APIRouter — lets this file define its own routes independently
# The router is registered in main.py; adding endpoints here requires no changes there
from fastapi import APIRouter

# Step 2: Create the router instance for segmentation-related endpoints
router = APIRouter()


# Step 3: POST /segment — stub returning a not-implemented marker
# In Step 3 this will accept a DICOM ZIP upload and trigger the TotalSegmentator pipeline
@router.post("/segment")
def post_segment():
    return {"status": "not implemented"}
