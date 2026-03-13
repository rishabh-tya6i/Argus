from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import Scan, ScanResult, ScanMetadata, Tenant, SandboxRun, SandboxStatus
from .dependencies import get_current_user_optional, get_api_key_context, CurrentTenant
from .model import model_instance
from .schemas import PredictRequest, PredictResponse
from .schemas_saas import ScanSummaryResponse, ScanDetailResponse
from .sandbox.queue import enqueue_sandbox_run


router = APIRouter(tags=["scans"])


def _persist_scan(
    db: Session,
    tenant_id: int,
    url: str,
    prediction: PredictResponse,
    request: Request,
    source: str | None,
    user_id: int | None,
) -> int:
    scan = Scan(
        tenant_id=tenant_id,
        url=url,
        source=source,
        created_by_user_id=user_id,
    )
    db.add(scan)
    db.flush()

    result = ScanResult(
        scan_id=scan.id,
        prediction=prediction.prediction,
        confidence=prediction.confidence,
        explanation=prediction.explanation.model_dump(),
    )
    db.add(result)

    meta = ScanMetadata(
        scan_id=scan.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        client_type=request.headers.get("x-client-type"),
        extra={},
    )
    db.add(meta)

    db.commit()
    return scan.id


@router.get("/scans", response_model=list[ScanSummaryResponse])
def list_scans(tenant: CurrentTenant, db: Session = Depends(get_db)):
    scans = (
        db.query(Scan, ScanResult)
        .join(ScanResult, Scan.id == ScanResult.scan_id)
        .filter(Scan.tenant_id == tenant.id)
        .order_by(Scan.created_at.desc())
        .limit(100)
        .all()
    )
    response: list[ScanSummaryResponse] = []
    for scan, result in scans:
        response.append(
            ScanSummaryResponse(
                id=scan.id,
                url=scan.url,
                source=scan.source,
                created_at=scan.created_at,
                prediction=result.prediction,
                confidence=float(result.confidence),
            )
        )
    return response


@router.get("/scans/{scan_id}", response_model=ScanDetailResponse)
def get_scan(scan_id: int, tenant: CurrentTenant, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id, Scan.tenant_id == tenant.id).first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    result = db.query(ScanResult).filter(ScanResult.scan_id == scan.id).first()
    meta = db.query(ScanMetadata).filter(ScanMetadata.scan_id == scan.id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan result not found")

    return ScanDetailResponse(
        id=scan.id,
        url=scan.url,
        source=scan.source,
        created_at=scan.created_at,
        prediction=result.prediction,
        confidence=float(result.confidence),
        explanation=result.explanation,
        client_type=meta.client_type if meta else None,
        ip_address=meta.ip_address if meta else None,
        user_agent=meta.user_agent if meta else None,
    )


@router.post("/scan", response_model=PredictResponse)
async def scan_url(
    req: PredictRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user_optional),
    _api_key=Depends(get_api_key_context),
):
    """
    Tenant-aware scan endpoint that mirrors /api/predict but always records a
    scan in the database.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context required")

    res = await model_instance.predict(req.url, req.html, req.screenshot, db=db)

    user = getattr(request.state, "user", None)
    user_id = user.id if user is not None else None
    source = getattr(req, "source", None) if hasattr(req, "source") else None

    scan_id = _persist_scan(
        db=db,
        tenant_id=tenant_id,
        url=req.url,
        prediction=res,
        request=request,
        source=source,
        user_id=user_id,
    )

    # Auto-enqueue sandbox analysis if above tenant threshold
    tenant = db.get(Tenant, tenant_id)
    if tenant:
        config = tenant.config or {}
        sandbox_threshold = float(config.get("sandbox_threshold", 0.85))
        if res.confidence >= sandbox_threshold:
            run = SandboxRun(
                tenant_id=tenant_id,
                scan_id=scan_id,
                url=req.url,
                status=SandboxStatus.queued,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            enqueue_sandbox_run(run.id)

    return res
