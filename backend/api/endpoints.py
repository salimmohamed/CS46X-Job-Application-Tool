# FastAPI endpoints for Job Hunting AI Tool.
# Combines resume parsing and encryption services.

from fastapi import FastAPI

app = FastAPI(title="Job Hunting AI Tool API")


@app.get("/")
async def health_check():
    # Health check endpoint
    return {"status": "healthy", "service": "Job Hunting AI Tool"}