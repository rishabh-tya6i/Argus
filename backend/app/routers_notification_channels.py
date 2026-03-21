from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .db import get_db
from .db_models import NotificationChannel
from .dependencies import get_current_active_user
from .schemas_saas import (
    NotificationChannelResponse,
    NotificationChannelCreateRequest,
    UserResponse,
)

router = APIRouter(prefix="/notification-channels", tags=["Notification Channels"])


@router.get("/", response_model=List[NotificationChannelResponse])
async def get_notification_channels(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    Get all notification channels configured for the current tenant.
    """
    return (
        db.query(NotificationChannel)
        .filter(NotificationChannel.tenant_id == current_user.tenant_id)
        .all()
    )


@router.post("/", response_model=NotificationChannelResponse)
async def create_notification_channel(
    channel_request: NotificationChannelCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    Create a new notification channel for the current tenant.
    """
    channel = NotificationChannel(
        tenant_id=current_user.tenant_id,
        type=channel_request.type,
        config=channel_request.config,
        is_active=channel_request.is_active,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    """
    Delete a notification channel.
    """
    channel = (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")

    db.delete(channel)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
