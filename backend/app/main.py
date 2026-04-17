# Step 1: Import FastAPI — the web framework that powers the OrthoCloud API
from fastapi import FastAPI

# Step 2: Import route modules — each file groups related endpoints together
# structures.py handles anatomy label queries; segment.py handles inference requests
from app.routes import structures, segment

# Step 3: Create the FastAPI application instance
# The title appears in the auto-generated /docs and /redoc pages
app = FastAPI(title="OrthoCloud API")

# Step 4: Register routers — attaches each module's endpoints to the main app
# Adding a new route group in Step 2 means adding one include_router call here
app.include_router(structures.router)
app.include_router(segment.router)


# Step 5: Health check endpoint
# Returns {"status": "ok"} — used by Docker and load balancers to confirm the app is running
@app.get("/health")
def health():
    return {"status": "ok"}
