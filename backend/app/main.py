"""
GreenFleet Q - FastAPI Backend Application
SIH26138: Quantum-Inspired Fuel Consumption Prediction and Green Fleet Optimization
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.app.api.data_routes import router as data_router
from backend.app.api.model_routes import router as model_router
from backend.app.api.optimize_routes import router as optimize_router
from backend.app.api.scenario_routes import router as scenario_router
from backend.app.api.benchmark_routes import router as benchmark_router
from backend.app.api.config_routes import router as config_router
from backend.app.api.report_routes import router as report_router
from backend.app.api.tools_routes import router as tools_router

app = FastAPI(
    title="GreenFleet Q API",
    description=(
        "Quantum-Inspired Fuel Consumption Prediction and Multi-Objective Fleet Optimization platform. "
        "Smart India Hackathon problem SIH26138."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Routers
API_V1_PREFIX = "/api/v1"
app.include_router(data_router, prefix=API_V1_PREFIX)
app.include_router(model_router, prefix=API_V1_PREFIX)
app.include_router(optimize_router, prefix=API_V1_PREFIX)
app.include_router(scenario_router, prefix=API_V1_PREFIX)
app.include_router(benchmark_router, prefix=API_V1_PREFIX)
app.include_router(config_router, prefix=API_V1_PREFIX)
app.include_router(report_router, prefix=API_V1_PREFIX)
app.include_router(tools_router, prefix=API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "service": "GreenFleet Q",
        "tagline": "Quantum-Inspired Fuel Consumption Prediction & Green Fleet Optimization",
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": "/api/v1",
    }


@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "quantum_circuit_simulator": "READY", "optimization_engine": "READY"}


# Mount built frontend SPA if available
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    from fastapi.responses import FileResponse
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
