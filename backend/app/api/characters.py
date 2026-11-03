"""Characters CRUD router – beheer van personages binnen een project."""

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.models import Character, CharacterExpression, Project
from app.schemas.schemas import CharacterCreate, CharacterResponse, CharacterUpdate, ExpressionResponse
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/characters", tags=["Characters"])

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _verify_project(project_id: str, session: Session) -> Project:
    """Verifieer dat het project bestaat."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    return project


from app.services.image_service import to_media_url


def _character_to_response(character: Character) -> CharacterResponse:
    """Converteer een Character model naar CharacterResponse."""
    expressions = [
        ExpressionResponse(
            id=expr.id,
            name=expr.name,
            image_path=expr.image_path,
            image_url=to_media_url(expr.image_path),
            mouth_open_path=expr.mouth_open_path,
            mouth_open_url=to_media_url(expr.mouth_open_path),
            mouth_closed_path=expr.mouth_closed_path,
            mouth_closed_url=to_media_url(expr.mouth_closed_path),
            created_at=expr.created_at,
        )
        for expr in character.expressions
    ]

    sprite_url = None
    if character.sprite_base_path:
        sprite_path = Path(character.sprite_base_path)
        if sprite_path.is_dir():
            candidate = sprite_path / "sprite_base.png"
            if candidate.exists() and candidate.stat().st_size > 0:
                sprite_url = to_media_url(str(candidate))
        elif sprite_path.exists() and sprite_path.stat().st_size > 0:
            sprite_url = to_media_url(str(sprite_path))
    if not sprite_url and expressions:
        sprite_url = expressions[0].image_url

    try:
        reference_images = json.loads(character.reference_images_json or "[]")
        if not isinstance(reference_images, list):
            reference_images = []
    except Exception:
        reference_images = []

    return CharacterResponse(
        id=character.id,
        project_id=character.project_id,
        name=character.name,
        description=character.description,
        personality=character.personality,
        voice_id=character.voice_id,
        voice_provider=character.voice_provider,
        voice_pitch=character.voice_pitch or "+15Hz",
        voice_rate=character.voice_rate or "+0%",
        sprite_base_path=character.sprite_base_path,
        sprite_url=sprite_url,
        style_prompt=character.style_prompt,
        visual_dna_prompt=character.visual_dna_prompt or "",
        color_palette=character.color_palette,
        reference_images=reference_images,
        reference_image_urls=[to_media_url(p) for p in reference_images if p],
        expressions=expressions,
        created_at=character.created_at,
        updated_at=character.updated_at,
    )


@router.get("", response_model=list[CharacterResponse])
@router.get("/", response_model=list[CharacterResponse])
async def list_characters(
    project_id: str,
    session: Session = Depends(get_session),
):
    """Lijst alle karakters op voor een project."""
    _verify_project(project_id, session)
    characters = session.exec(
        select(Character).where(Character.project_id == project_id).order_by(Character.name)
    ).all()
    return [_character_to_response(c) for c in characters]


@router.post("", response_model=CharacterResponse, status_code=201)
@router.post("/", response_model=CharacterResponse, status_code=201)
async def create_character(
    project_id: str,
    data: CharacterCreate,
    session: Session = Depends(get_session),
):
    """Maak een nieuw karakter aan voor een project."""
    _verify_project(project_id, session)
    character = Character(
        project_id=project_id,
        name=data.name,
        description=data.description,
        personality=data.personality,
        voice_id=data.voice_id,
        voice_provider=data.voice_provider,
        style_prompt=data.style_prompt,
        visual_dna_prompt=data.visual_dna_prompt or "",
        color_palette=data.color_palette,
    )
    session.add(character)
    session.commit()
    session.refresh(character)
    return _character_to_response(character)


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    project_id: str,
    character_id: str,
    session: Session = Depends(get_session),
):
    """Haal een karakter op met alle expressies."""
    _verify_project(project_id, session)
    character = session.get(Character, character_id)
    if character is None or character.project_id != project_id:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")
    return _character_to_response(character)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    project_id: str,
    character_id: str,
    data: CharacterUpdate,
    session: Session = Depends(get_session),
):
    """Werk een bestaand karakter bij."""
    _verify_project(project_id, session)
    character = session.get(Character, character_id)
    if character is None or character.project_id != project_id:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    update_data = data.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(character, field_name, value)
    character.updated_at = datetime.now(timezone.utc)

    session.add(character)
    session.commit()
    session.refresh(character)
    return _character_to_response(character)


@router.delete("/{character_id}")
async def delete_character(
    project_id: str,
    character_id: str,
    session: Session = Depends(get_session),
):
    """Verwijder een karakter en alle expressies (cascade)."""
    _verify_project(project_id, session)
    character = session.get(Character, character_id)
    if character is None or character.project_id != project_id:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")
    session.delete(character)
    session.commit()
    return {"detail": f"Karakter '{character.name}' verwijderd."}


@router.post("/{character_id}/expressions", response_model=ExpressionResponse, status_code=201)
async def upload_expression(
    project_id: str,
    character_id: str,
    name: str = "neutral",
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload een expressie-afbeelding voor een karakter (multipart form)."""
    _verify_project(project_id, session)
    character = session.get(Character, character_id)
    if character is None or character.project_id != project_id:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Ongeldig bestandstype: {file.content_type}. "
            f"Toegestaan: {', '.join(_ALLOWED_IMAGE_TYPES)}",
        )

    # Sla de afbeelding op in de characters directory
    char_dir = settings.characters_dir / character_id
    char_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".png"
    filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = char_dir / filename

    content = await file.read()
    file_path.write_bytes(content)

    expression = CharacterExpression(
        character_id=character_id,
        name=name,
        image_path=str(file_path),
    )
    session.add(expression)
    session.commit()
    session.refresh(expression)

    def _url(path: str | None) -> str | None:
        if not path:
            return None
        return f"/media/characters/{character_id}/{Path(path).name}"

    return ExpressionResponse(
        id=expression.id,
        name=expression.name,
        image_path=expression.image_path,
        image_url=_url(expression.image_path),
        mouth_open_path=expression.mouth_open_path,
        mouth_open_url=_url(expression.mouth_open_path),
        mouth_closed_path=expression.mouth_closed_path,
        mouth_closed_url=_url(expression.mouth_closed_path),
        created_at=expression.created_at,
    )


@router.post("/{character_id}/generate-sprite")
async def generate_sprite(
    project_id: str,
    character_id: str,
    emotion: str = "blij",
    session: Session = Depends(get_session),
):
    """Genereer een sprite voor een karakter via de image service (achtergrondtaak)."""
    _verify_project(project_id, session)
    character = session.get(Character, character_id)
    if character is None or character.project_id != project_id:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    task_id = f"sprite-{character_id}-{uuid.uuid4().hex[:8]}"
    character_description = character.description or character.name
    character_style = character.style_prompt or "3d Pixar character sprite"

    async def _generate():
        from app.services.image_service import image_service

        task_manager.update_progress(task_id, 0.1, "Sprite generatie gestart...")

        output_dir = settings.characters_dir / character_id
        output_dir.mkdir(parents=True, exist_ok=True)

        task_manager.update_progress(task_id, 0.3, f"Karakter sprite ({emotion}) genereren...")
        result = await image_service.generate_character_sprite(
            description=character_description,
            emotion=emotion,
            style_prompt=character_style,
            output_dir=str(output_dir),
        )

        task_manager.update_progress(task_id, 0.8, "Opslaan in database...")
        from app.core.database import get_engine
        from sqlmodel import Session as SyncSession

        engine = get_engine()
        with SyncSession(engine) as db:
            char = db.get(Character, character_id)
            if char:
                char.sprite_base_path = result.get("sprite_path")
                char.updated_at = datetime.now(timezone.utc)
                db.add(char)

                expr = db.exec(
                    select(CharacterExpression)
                    .where(CharacterExpression.character_id == character_id)
                    .where(CharacterExpression.name == emotion)
                ).first()
                if not expr:
                    expr = CharacterExpression(
                        character_id=character_id,
                        name=emotion,
                        image_path=result.get("sprite_path", ""),
                        mouth_open_path=result.get("mouth_open_path"),
                        mouth_closed_path=result.get("mouth_closed_path"),
                    )
                else:
                    expr.image_path = result.get("sprite_path", "")
                    expr.mouth_open_path = result.get("mouth_open_path")
                    expr.mouth_closed_path = result.get("mouth_closed_path")
                db.add(expr)
                db.commit()

        task_manager.update_progress(task_id, 1.0, "Sprite generatie voltooid")
        return result

    task_manager.start_task(task_id, _generate())
    return {"task_id": task_id, "detail": f"Sprite generatie voor '{emotion}' gestart."}


@router.post("/{character_id}/upload-reference", response_model=CharacterResponse)
async def upload_character_reference(
    project_id: str,
    character_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload een referentie-afbeelding voor consistent uiterlijk (max 3 referentiebeelden)."""
    _verify_project(project_id, session)
    character = session.get(Character, character_id)
    if not character or character.project_id != project_id:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    ext = Path(file.filename or "ref.png").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        ext = ".png"

    filename = f"ref_{character_id}_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:4]}{ext}"
    dest = settings.characters_dir / filename
    dest.write_bytes(await file.read())

    try:
        current_refs = json.loads(character.reference_images_json or "[]")
        if not isinstance(current_refs, list):
            current_refs = []
    except Exception:
        current_refs = []

    # Maximaal 3 referentie-afbeeldingen
    if len(current_refs) >= 3:
        current_refs.pop(0)
    current_refs.append(str(dest))

    character.reference_images_json = json.dumps(current_refs, ensure_ascii=False)
    character.updated_at = datetime.now(timezone.utc)
    session.add(character)
    session.commit()
    session.refresh(character)
    return _character_to_response(character)


@router.delete("/{character_id}/reference/{index}", response_model=CharacterResponse)
async def delete_character_reference(
    project_id: str,
    character_id: str,
    index: int,
    session: Session = Depends(get_session),
):
    """Verwijder een specifieke referentie-afbeelding van een karakter."""
    _verify_project(project_id, session)
    character = session.get(Character, character_id)
    if not character or character.project_id != project_id:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    try:
        current_refs = json.loads(character.reference_images_json or "[]")
        if not isinstance(current_refs, list):
            current_refs = []
    except Exception:
        current_refs = []

    if 0 <= index < len(current_refs):
        removed = current_refs.pop(index)
        if os.path.exists(removed):
            try:
                os.remove(removed)
            except Exception:
                pass
        character.reference_images_json = json.dumps(current_refs, ensure_ascii=False)
        character.updated_at = datetime.now(timezone.utc)
        session.add(character)
        session.commit()
        session.refresh(character)

    return _character_to_response(character)
