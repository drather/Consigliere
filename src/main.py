from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from core.logger import get_logger

from api.routers.career import router as career_router
from api.routers.system import router as system_router
from api.routers.finance import router as finance_router
from api.routers.real_estate import router as real_estate_router
from api.routers.automation import router as automation_router
from api.routers.notify import router as notify_router

logger = get_logger(__name__)

app = FastAPI(title="Consigliere API", description="Personal Knowledge Agent API")

# Include routers
app.include_router(career_router)
app.include_router(system_router)
app.include_router(finance_router)
app.include_router(real_estate_router)
app.include_router(automation_router)
app.include_router(notify_router)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Consigliere Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
