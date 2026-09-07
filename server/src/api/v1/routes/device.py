# server/src/api/v1/routes/devices.py
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate
from src.core.database import async_session
from src.models.device import Device

router = APIRouter()


@router.post("/", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(payload: DeviceCreate) -> DeviceRead:
    async with async_session() as session:  # type: AsyncSession
        async with session.begin():
            stmt = (
                insert(Device)
                .values(
                    facility_id=payload.facility_id,
                    name=payload.name,
                    device_type=payload.device_type,
                    ph_setpoint=payload.ph_setpoint,
                    thresholds=(
                        payload.thresholds.dict() if payload.thresholds else None
                    ),
                )
                .returning(Device)
            )
            result = await session.execute(stmt)
            created = result.scalar_one()
            # ensure we have ORM instance
            if not isinstance(created, Device):
                q = select(Device).where(Device.id == created.id)
                res = await session.execute(q)
                created = res.scalar_one()
        return DeviceRead.from_orm(created)


@router.get("/", response_model=List[DeviceRead])
async def list_devices(limit: int = 100) -> List[DeviceRead]:
    async with async_session() as session:
        q = select(Device).limit(limit)
        result = await session.execute(q)
        devices = result.scalars().all()
        return [DeviceRead.from_orm(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(device_id: str) -> DeviceRead:
    async with async_session() as session:
        q = select(Device).where(Device.id == device_id)
        result = await session.execute(q)
        device = result.scalar_one_or_none()
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
            )
        return DeviceRead.from_orm(device)


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(device_id: str, payload: DeviceUpdate):
    async with async_session() as session:
        async with session.begin():
            values = {}
            if payload.name is not None:
                values["name"] = payload.name
            if payload.ph_setpoint is not None:
                values["ph_setpoint"] = payload.ph_setpoint
            if payload.is_online is not None:
                values["is_online"] = payload.is_online
            if payload.thresholds is not None:
                values["thresholds"] = payload.thresholds.dict()

            if not values:
                q = select(Device).where(Device.id == device_id)
                res = await session.execute(q)
                device = res.scalar_one_or_none()
                if device is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
                    )
                return DeviceRead.from_orm(device)

            stmt = (
                update(Device)
                .where(Device.id == device_id)
                .values(**values)
                .returning(Device)
            )
            result = await session.execute(stmt)
            updated = result.scalar_one_or_none()
            if updated is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Device not found"
                )
            return DeviceRead.from_orm(updated)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str):
    async with async_session() as session:
        async with session.begin():
            stmt = delete(Device).where(Device.id == device_id)
            result = await session.execute(stmt)
            # result.rowcount may not be available with async drivers; do a select to confirm
            q = select(Device).where(Device.id == device_id)
            res = await session.execute(q)
            device = res.scalar_one_or_none()
            if device is not None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete device",
                )
    return None
