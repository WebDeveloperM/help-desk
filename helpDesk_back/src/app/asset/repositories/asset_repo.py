"""Asset repository implementation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, cast, delete, func, insert, or_, select, update
from sqlalchemy import String as SAString
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.asset.models import Asset
from app.asset.repositories.interfaces import AssetRepository
from app.asset.schemas import AssetCreate, AssetFilterParams, AssetUpdate
from app.core.enums import TicketStatus
from app.ticket.models import Ticket, TicketCategory, ticket_assets_table


class SQLAlchemyAssetRepository(AssetRepository):
    """SQLAlchemy-based repository for assets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, asset_id: UUID) -> Asset | None:
        """Return asset by ID with relationships loaded."""
        result = await self.session.execute(
            select(Asset)
            .options(
                selectinload(Asset.department),
                selectinload(Asset.assigned_user),
                selectinload(Asset.tickets),
            )
            .where(Asset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, asset_ids: list[UUID]) -> list[Asset]:
        """Return assets by IDs."""
        if not asset_ids:
            return []
        result = await self.session.execute(
            select(Asset)
            .options(
                selectinload(Asset.department),
                selectinload(Asset.assigned_user),
                selectinload(Asset.tickets),
            )
            .where(Asset.id.in_(asset_ids))
        )
        return list[Asset](result.scalars().all())

    async def get_by_inventory_number(self, inventory_number: str) -> Asset | None:
        """Return asset by inventory number."""
        result = await self.session.execute(
            select(Asset).where(Asset.inventory_number == inventory_number)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        asset_data: AssetCreate,
        embedding: list[float],
    ) -> Asset:
        """Create and persist a new asset."""
        asset = Asset(
            **asset_data.model_dump(),
            image_urls=[],
            embedding=embedding,
        )
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        loaded = await self.get_by_id(asset.id)
        return loaded if loaded is not None else asset

    async def update(
        self,
        asset_id: UUID,
        asset_data: AssetUpdate,
        embedding: list[float] | None = None,
    ) -> Asset | None:
        """Partially update an asset."""
        update_data: dict[str, Any] = {
            k: v for k, v in asset_data.model_dump(exclude_unset=True).items()
        }
        if embedding is not None:
            update_data["embedding"] = embedding
        if not update_data:
            return await self.get_by_id(asset_id)

        await self.session.execute(
            update(Asset).where(Asset.id == asset_id).values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_id(asset_id)

    async def soft_delete(self, asset_id: UUID) -> Asset | None:
        """Soft-delete an asset."""
        await self.session.execute(
            update(Asset).where(Asset.id == asset_id).values(is_active=False)
        )
        await self.session.flush()
        return await self.get_by_id(asset_id)

    async def list_with_cursor(
        self,
        filters: AssetFilterParams,
        *,
        restrict_department_id: UUID | None,
        similarity_embedding: list[float] | None,
        cursor_value: str | None,
        cursor_id: UUID | None,
    ) -> tuple[list[Asset], str | None, UUID | None]:
        """Return assets using cursor pagination."""
        limit = filters.limit + 1
        similarity_mode = bool(filters.similarity_query and similarity_embedding)
        if similarity_mode:
            distance_expr = Asset.embedding.cosine_distance(similarity_embedding).label(
                "distance"
            )
            query = select(Asset, distance_expr).options(
                selectinload(Asset.department),
                selectinload(Asset.assigned_user),
                selectinload(Asset.tickets),
            )
        else:
            query = select(Asset).options(
                selectinload(Asset.department),
                selectinload(Asset.assigned_user),
                selectinload(Asset.tickets),
            )

        if not filters.include_inactive:
            query = query.where(Asset.is_active.is_(True))
        if restrict_department_id is not None:
            query = query.where(Asset.department_id == restrict_department_id)
        if filters.department_id is not None:
            query = query.where(Asset.department_id == filters.department_id)
        if filters.asset_type:
            query = query.where(Asset.asset_type == filters.asset_type)
        if filters.status is not None:
            query = query.where(Asset.status == filters.status)
        if filters.search:
            pattern = f"%{filters.search}%"
            query = query.where(
                or_(
                    Asset.name.ilike(pattern),
                    Asset.inventory_number.ilike(pattern),
                )
            )

        if similarity_mode:
            if cursor_value and cursor_id:
                cursor_distance = float(cursor_value)
                query = query.where(
                    or_(
                        distance_expr > cursor_distance,
                        and_(distance_expr == cursor_distance, Asset.id > cursor_id),
                    )
                )
            query = query.order_by(distance_expr.asc(), Asset.id.asc()).limit(limit)
            result = await self.session.execute(query)
            rows = result.all()
            assets = [row[0] for row in rows]
            has_more = len(assets) > filters.limit
            if has_more:
                assets = assets[: filters.limit]
                rows = rows[: filters.limit]
            if not assets:
                return [], None, None
            if not has_more:
                return assets, None, None
            last_distance = rows[-1][1]
            return assets, str(last_distance), assets[-1].id

        sort_column = (
            Asset.name
            if filters.sort_by == "name"
            else cast(Asset.status, SAString)
        )
        is_asc = filters.sort_order == "asc"
        if cursor_value and cursor_id:
            if is_asc:
                query = query.where(
                    or_(
                        sort_column > cursor_value,
                        and_(sort_column == cursor_value, Asset.id > cursor_id),
                    )
                )
            else:
                query = query.where(
                    or_(
                        sort_column < cursor_value,
                        and_(sort_column == cursor_value, Asset.id < cursor_id),
                    )
                )

        if is_asc:
            query = query.order_by(sort_column.asc(), Asset.id.asc())
        else:
            query = query.order_by(sort_column.desc(), Asset.id.desc())
        query = query.limit(limit)
        result = await self.session.execute(query)
        assets = list(result.scalars().all())
        has_more = len(assets) > filters.limit
        if has_more:
            assets = assets[: filters.limit]

        if not assets or not has_more:
            return assets, None, None
        last_asset = assets[-1]
        last_cursor_value = (
            last_asset.name if filters.sort_by == "name" else last_asset.status.value
        )
        return assets, last_cursor_value, last_asset.id

    async def append_image_url(self, asset_id: UUID, image_url: str) -> Asset | None:
        """Append image URL to asset."""
        asset = await self.get_by_id(asset_id)
        if asset is None:
            return None
        urls = list(asset.image_urls or [])
        urls.append(image_url)
        asset.image_urls = urls
        await self.session.flush()
        await self.session.refresh(asset)
        return await self.get_by_id(asset_id)

    async def remove_image_url(self, asset_id: UUID, image_url: str) -> Asset | None:
        """Remove image URL from asset."""
        asset = await self.get_by_id(asset_id)
        if asset is None:
            return None
        asset.image_urls = [url for url in asset.image_urls if url != image_url]
        await self.session.flush()
        await self.session.refresh(asset)
        return await self.get_by_id(asset_id)

    async def has_active_repair_ticket(
        self,
        asset_id: UUID,
        exclude_ticket_id: UUID | None = None,
    ) -> bool:
        """Return True if asset has active repair ticket."""
        active_statuses = [
            TicketStatus.ASSIGNED,
            TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING_INFO,
        ]
        query = (
            select(func.count())
            .select_from(ticket_assets_table)
            .join(Ticket, Ticket.id == ticket_assets_table.c.ticket_id)
            .join(TicketCategory, TicketCategory.id == Ticket.category_id)
            .where(ticket_assets_table.c.asset_id == asset_id)
            .where(TicketCategory.code == "repair")
            .where(Ticket.status.in_(active_statuses))
        )
        if exclude_ticket_id is not None:
            query = query.where(Ticket.id != exclude_ticket_id)
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return int(count) > 0

    async def set_ticket_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """Replace ticket assets for ticket."""
        await self.session.execute(
            delete(ticket_assets_table).where(ticket_assets_table.c.ticket_id == ticket_id)
        )
        await self.session.flush()
        unique_asset_ids = list(dict.fromkeys(asset_ids))
        for asset_id in unique_asset_ids:
            await self.session.execute(
                insert(ticket_assets_table).values(ticket_id=ticket_id, asset_id=asset_id)
            )
        await self.session.flush()

    async def add_ticket_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """Attach assets to ticket and skip existing links."""
        if not asset_ids:
            return
        existing_result = await self.session.execute(
            select(ticket_assets_table.c.asset_id).where(
                ticket_assets_table.c.ticket_id == ticket_id
            )
        )
        existing = set(existing_result.scalars().all())
        for asset_id in dict.fromkeys(asset_ids):
            if asset_id in existing:
                continue
            await self.session.execute(
                insert(ticket_assets_table).values(ticket_id=ticket_id, asset_id=asset_id)
            )
        await self.session.flush()

    async def remove_ticket_asset(self, ticket_id: UUID, asset_id: UUID) -> None:
        """Detach a single asset from ticket."""
        await self.session.execute(
            delete(ticket_assets_table)
            .where(ticket_assets_table.c.ticket_id == ticket_id)
            .where(ticket_assets_table.c.asset_id == asset_id)
        )
        await self.session.flush()
