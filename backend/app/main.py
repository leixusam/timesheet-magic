from fastapi import FastAPI

app = FastAPI(title="TimeSheet Magic API")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# Placeholder for future root path information or actions
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to TimeSheet Magic API"} 