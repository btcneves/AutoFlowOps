from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace


async def get_or_create_default_workspace(session: AsyncSession) -> Workspace:
    result = await session.execute(
        select(Workspace).where(Workspace.is_default.is_(True))
    )
    workspace = result.scalar_one_or_none()
    if workspace is not None:
        return workspace

    result = await session.execute(select(Workspace).limit(1))
    workspace = result.scalar_one_or_none()
    if workspace is not None:
        await session.execute(
            update(Workspace)
            .where(Workspace.id == workspace.id)
            .values(is_default=True)
        )
        await session.commit()
        await session.refresh(workspace)
        return workspace

    workspace = Workspace(name="Default", slug="default", is_default=True)
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return workspace
