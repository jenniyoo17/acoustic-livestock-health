import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.audit import AuditBlockResponse, AuditIntegrityResponse
from app.services.audit import list_audit_blocks, verify_audit_chain

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chain", response_model=list[AuditBlockResponse])
async def get_audit_chain(
    db: AsyncSession = Depends(get_session),
) -> list[AuditBlockResponse]:
    try:
        blocks = await list_audit_blocks(db)
    except SQLAlchemyError as error:
        logger.exception("Unable to read the audit chain")
        raise HTTPException(status_code=503, detail="Audit ledger is unavailable") from error
    return [AuditBlockResponse.model_validate(block) for block in blocks]


@router.post("/verify-integrity", response_model=AuditIntegrityResponse)
async def verify_integrity(
    db: AsyncSession = Depends(get_session),
) -> AuditIntegrityResponse:
    try:
        result = await verify_audit_chain(db)
    except SQLAlchemyError as error:
        logger.exception("Unable to verify the audit chain")
        raise HTTPException(status_code=503, detail="Audit integrity check is unavailable") from error
    return AuditIntegrityResponse(
        valid=result.valid,
        checked_blocks=result.checked_blocks,
        error=result.error,
    )