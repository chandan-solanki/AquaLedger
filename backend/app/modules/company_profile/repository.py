import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company_profile.models import CompanyProfile


class CompanyProfileRepository:
    """All raw queries for the company_profile module live here -
    service.py never builds SQL directly."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_tenant(self, tenant_id: uuid.UUID) -> CompanyProfile | None:
        result = await self._session.execute(
            select(CompanyProfile).where(CompanyProfile.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def add(self, profile: CompanyProfile) -> CompanyProfile:
        """Stages the insert - id is a client-side uuid7() default, so no
        flush is needed here. The service commits (and can catch the
        unique tenant_id violation from a concurrent first-vivify) as a
        single, deliberate step."""
        self._session.add(profile)
        return profile
