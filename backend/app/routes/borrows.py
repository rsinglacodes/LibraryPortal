from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.models.user import User
from app.schemas.admin import BorrowRecordResponse, ReturnWithInspectionResponse
from app.services import borrow_service
from app.services.roboflow_service import RoboflowError, check_damage

router = APIRouter(prefix="/borrows", tags=["borrows"])

# Allowed MIME types for damage-inspection image uploads
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


class StudentBorrowRequest(BaseModel):
    isbn10: str
    days: int = 14


@router.get("/my", response_model=list[BorrowRecordResponse])
def get_my_borrow_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BorrowRecordResponse]:
    return borrow_service.get_user_borrows(db, current_user.roll_number)


@router.post("/borrow", response_model=BorrowRecordResponse, status_code=status.HTTP_201_CREATED)
def borrow_book(
    payload: StudentBorrowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    return borrow_service.student_borrow_book(
        db=db,
        roll_number=current_user.roll_number,
        isbn10=payload.isbn10,
        days=payload.days,
    )


@router.post("/return/{borrow_id}", response_model=BorrowRecordResponse)
def return_book(
    borrow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    return borrow_service.student_return_book(
        db=db,
        roll_number=current_user.roll_number,
        borrow_id=borrow_id,
    )


@router.post(
    "/return-with-inspection/{borrow_id}",
    response_model=ReturnWithInspectionResponse,
)
async def return_book_with_inspection(
    borrow_id: int,
    file: UploadFile = File(..., description="Image of the book (jpg/jpeg/png/webp, max 10 MB)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReturnWithInspectionResponse:
    """
    Return a book with Roboflow damage inspection.

    1. Validates the uploaded image (type + size).
    2. Sends the image to Roboflow for damage detection.
    3. If damage is detected the backend applies a ₹100 fine (never trusted from frontend).
    4. Completes the return and persists the damage info.
    """
    # ── Validate file type ────────────────────────────────────────────────────
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid image type. Please upload a JPG, JPEG, PNG, or WEBP image.",
        )

    # ── Read & validate file size ─────────────────────────────────────────────
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty. Please upload a valid book image.",
        )
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image is too large. Maximum allowed size is 10 MB.",
        )

    # ── Call Roboflow ─────────────────────────────────────────────────────────
    try:
        damage_detected, damage_labels = check_damage(image_bytes)
    except RoboflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not check book condition right now: {exc}. Please try again.",
        )

    # Store a compact base64 representation for the admin image preview
    damage_image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # ── Complete return + persist damage info ─────────────────────────────────
    return borrow_service.student_return_book_with_inspection(
        db=db,
        roll_number=current_user.roll_number,
        borrow_id=borrow_id,
        damage_detected=damage_detected,
        damage_types=damage_labels,
        damage_image_b64=damage_image_b64,
    )
