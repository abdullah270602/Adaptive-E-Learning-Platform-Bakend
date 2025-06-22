import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user
from app.database.connection import PostgresConnection
from app.database.learning_profile_queries import get_learning_profile_by_user
from app.schemas.diagrams import DiagramRequest, DiagramResponse
from app.services.diagram_generator import generate_diagrams

router = APIRouter(prefix="/diagrams", tags=["Diagrams"])


@router.post("/generate", response_model=DiagramResponse, status_code=status.HTTP_200_OK)
async def generate_diagram_endpoint(
    request: DiagramRequest,
    current_user: str = Depends(get_current_user)
):
    try:
        with PostgresConnection() as conn:
            profile = get_learning_profile_by_user(conn, current_user)
            if not profile:
                raise HTTPException(status_code=404, detail="Learning profile not found")

        diagrams = await generate_diagrams(
            content=request.content,
            summary=request.summary,
            learning_profile=profile
        )

        return {"diagrams": diagrams}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate diagrams")
