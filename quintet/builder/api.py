"""
Build Mode HTTP API
====================

FastAPI server exposing Build Mode endpoints.

Endpoints:
- POST /detect      - Detect build intent
- POST /blueprint   - Generate blueprint
- POST /build       - Execute build
- POST /full        - Full pipeline (detect + blueprint + build)
- GET  /status      - System status
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from quintet.builder.ultra_mode import UltraModeOrchestrator, create_build_mode
from quintet.core.types import SPEC_VERSION


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

if FASTAPI_AVAILABLE:
    class DetectRequest(BaseModel):
        query: str
        synthesis: Optional[Dict[str, Any]] = None
    
    class BlueprintRequest(BaseModel):
        query: str
        synthesis: Optional[Dict[str, Any]] = None
        project_root: Optional[str] = None
    
    class BuildRequest(BaseModel):
        query: str
        synthesis: Optional[Dict[str, Any]] = None
        project_root: Optional[str] = None
        dry_run: bool = False
        auto_approve: bool = True


# =============================================================================
# API SERVER
# =============================================================================

def create_build_api(
    project_root: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
):
    """
    Create FastAPI application for Build Mode.
    
    Returns None if FastAPI is not installed.
    """
    if not FASTAPI_AVAILABLE:
        return None
    
    app = FastAPI(
        title="Quintet Build API",
        description="Ultra Mode 2.0 Build API",
        version=SPEC_VERSION
    )
    
    # Create orchestrator
    orchestrator = create_build_mode(project_root, config)
    
    @app.get("/status")
    async def status():
        """Get system status."""
        return {
            "status": "ok",
            "spec_version": SPEC_VERSION,
            "mode": "build",
            "project_root": orchestrator.project_root or "not set"
        }
    
    @app.post("/detect")
    async def detect(request: DetectRequest):
        """Detect build intent from query."""
        try:
            intent = orchestrator.detect(request.query, request.synthesis)
            return {
                "is_build": intent.is_build,
                "confidence": intent.confidence,
                "category": intent.category.value,
                "description": intent.description,
                "target_files": intent.target_files,
                "technologies": intent.technologies,
                "keywords_matched": intent.keywords_matched
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/blueprint")
    async def blueprint(request: BlueprintRequest):
        """Generate build blueprint."""
        try:
            # Create fresh orchestrator if different project root
            orch = orchestrator
            if request.project_root:
                orch = create_build_mode(request.project_root, config)
            
            intent = orch.detect(request.query, request.synthesis)
            if not intent.is_build:
                return {
                    "success": False,
                    "error": "Query does not appear to be a build request"
                }
            
            context = orch.spec_generator.scan_project()
            bp = orch.spec_generator.generate_blueprint(intent, context, request.synthesis)
            
            return {
                "success": True,
                "blueprint": bp.to_dict(),
                "context": context.to_dict()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/build")
    async def build(request: BuildRequest):
        """Execute a build."""
        try:
            # Create fresh orchestrator if different project root
            build_config = config.copy() if config else {}
            build_config["dry_run"] = request.dry_run
            
            orch = create_build_mode(request.project_root, build_config)
            
            # Set up approval based on auto_approve
            if not request.auto_approve:
                # In a real implementation, this would await user approval
                # For now, we just proceed
                pass
            
            result = orch.process(request.query, request.synthesis)
            
            return result.to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/full")
    async def full_pipeline(request: BuildRequest):
        """Run full build pipeline (detect + blueprint + build)."""
        try:
            build_config = config.copy() if config else {}
            build_config["dry_run"] = request.dry_run
            
            orch = create_build_mode(request.project_root, build_config)
            result = orch.process(request.query, request.synthesis)
            
            return result.to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    project_root: Optional[str] = None
):
    """
    Run the Build API server.
    
    Requires uvicorn to be installed.
    """
    if not FASTAPI_AVAILABLE:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
        return
    
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install uvicorn")
        return
    
    app = create_build_api(project_root)
    uvicorn.run(app, host=host, port=port)


# =============================================================================
# MODULE-LEVEL APP (for uvicorn quintet.builder.api:app)
# =============================================================================

# Create a default app instance for direct uvicorn usage
# This allows: uvicorn quintet.builder.api:app --host 127.0.0.1 --port 8000
app = create_build_api() if FASTAPI_AVAILABLE else None


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Quintet Build API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--project-root", default=None, help="Project root directory")
    
    args = parser.parse_args()
    run_server(args.host, args.port, args.project_root)

