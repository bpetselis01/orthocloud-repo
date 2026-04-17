# Step 1: Base image
# Python 3.11 slim keeps the image small — no build tools included by default
# Use the exact version to ensure reproducible builds across environments
FROM python:3.11-slim

# Step 2: Set working directory
# All subsequent commands run relative to /app inside the container
WORKDIR /app

# Step 3: Install dependencies first (before copying source)
# Docker caches this layer separately — if requirements.txt hasn't changed,
# pip install is skipped on rebuild, making builds significantly faster
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Copy application source code
# Done after pip install so source changes don't invalidate the dependency cache
COPY app/ ./app/

# Step 5: Expose the port Uvicorn will listen on
# Must match PORT in .env.example and the ports mapping in docker-compose.yml
EXPOSE 8000

# Step 6: Start the FastAPI app with Uvicorn
# --reload enables live reload when source files change (development only)
# In production this would be replaced with a gunicorn + uvicorn worker command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
