from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.item import ItemCreate, ItemOut, ItemUpdate
from app.services import item_service

# Every route in this router requires a logged-in user.
router = APIRouter(prefix="/api", tags=["items"], dependencies=[Depends(get_current_user)])


@router.get("/items", response_model=list[ItemOut])
def list_items(
    search: str | None = None,
    category: str | None = None,
    low_stock: bool = False,
    db: Session = Depends(get_db),
):
    return item_service.list_items(db, search=search, category=category, low_stock_only=low_stock)


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    return item_service.list_categories(db)


@router.post("/items", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(body: ItemCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    return item_service.create_item(db, user_id=user.id, **body.model_dump())


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return item_service.get_item(db, item_id)


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, body: ItemUpdate, db: Session = Depends(get_db)):
    # exclude_unset: distinguish "field not sent" from "field sent as null".
    return item_service.update_item(db, item_id, body.model_dump(exclude_unset=True))


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item_service.delete_item(db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
