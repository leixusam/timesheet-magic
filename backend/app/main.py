from fastapi import FastAPI
from app.api.endpoints.analysis import router as analysis_router

app = FastAPI(title="TimeSheet Magic API")

# Include the analysis endpoints
app.include_router(analysis_router, tags=["Analysis"])

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# Placeholder for future root path information or actions
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to TimeSheet Magic API"} 