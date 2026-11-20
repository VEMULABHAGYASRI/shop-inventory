from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, get_notifier
from app.models import User
from app.notifications import Notifier
from app.schemas.movement import MovementCreate, MovementOut
from app.services import stock_service

router = APIRouter(prefix="/api", tags=["stock"], dependencies=[Depends(get_current_user)])


@router.post("/items/{item_id}/movements", response_model=MovementOut,
             status_code=status.HTTP_201_CREATED)
def record_movement(
    item_id: int,
    body: MovementCreate,
    db: Session = Depends(get_db),
    notifier: Notifier = Depends(get_notifier),
    user: User = Depends(get_current_user),
):
    return stock_service.record_movement(
        db, notifier, item_id=item_id, change=body.change,
        reason=body.reason.value, note=body.note, user_id=user.id,
    )


@router.get("/items/{item_id}/movements", response_model=list[MovementOut])
def item_history(item_id: int, limit: int = Query(50, ge=1, le=500),
                 db: Session = Depends(get_db)):
    return stock_service.list_movements(db, item_id=item_id, limit=limit)


@router.get("/movements", response_model=list[MovementOut])
def recent_activity(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return stock_service.list_movements(db, limit=limit)
