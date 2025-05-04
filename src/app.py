from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from actions.data_actions import router as data_router
from actions.auth_actions import router as auth_router

app = FastAPI(
    title="Personal MS Assistant ChatGPT Actions",
    description="API endpoints for ChatGPT actions integration",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(data_router)

@app.get("/")
async def root():
    return {"message": "Personal MS Assistant ChatGPT Actions API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 