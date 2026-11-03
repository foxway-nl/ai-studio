"""Projects CRUD router – beheer van projecten."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app.core.database import get_session
from app.models.models import Character, Episode, Project
from app.schemas.schemas import ProjectCreate, ProjectResponse, ProjectUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def _project_to_response(project: Project, session: Session) -> ProjectResponse:
    """Converteer een Project model naar een ProjectResponse met tellingen."""
    episode_count = session.exec(
        select(func.count(Episode.id)).where(Episode.project_id == project.id)
    ).one()
    character_count = session.exec(
        select(func.count(Character.id)).where(Character.project_id == project.id)
    ).one()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        target_age_min=project.target_age_min,
        target_age_max=project.target_age_max,
        language=project.language,
        channel_name=project.channel_name,
        thumbnail_path=project.thumbnail_path,
        episode_count=episode_count,
        character_count=character_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=list[ProjectResponse])
@router.get("/", response_model=list[ProjectResponse])
async def list_projects(session: Session = Depends(get_session)):
    """Lijst alle projecten op met episode- en karaktertellingen."""
    projects = session.exec(
        select(Project).order_by(Project.updated_at.desc())  # type: ignore[attr-defined]
    ).all()
    return [_project_to_response(p, session) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    session: Session = Depends(get_session),
):
    """Maak een nieuw project aan."""
    project = Project(
        name=data.name,
        description=data.description,
        target_age_min=data.target_age_min,
        target_age_max=data.target_age_max,
        language=data.language,
        channel_name=data.channel_name,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return _project_to_response(project, session)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: Session = Depends(get_session),
):
    """Haal een project op op basis van ID."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    return _project_to_response(project, session)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    session: Session = Depends(get_session),
):
    """Werk een bestaand project bij."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")

    update_data = data.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(project, field_name, value)
    project.updated_at = datetime.now(timezone.utc)

    session.add(project)
    session.commit()
    session.refresh(project)
    return _project_to_response(project, session)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    session: Session = Depends(get_session),
):
    """Verwijder een project en alle gerelateerde data (cascade)."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    session.delete(project)
    session.commit()
    return {"detail": f"Project '{project.name}' en alle gerelateerde data verwijderd."}
