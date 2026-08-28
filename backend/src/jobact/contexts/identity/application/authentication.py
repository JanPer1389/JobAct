"""Shared account tenancy and session lifecycle for authentication handlers."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from jobact.contexts.identity.domain.membership import Membership
from jobact.contexts.identity.domain.organization import Organization
from jobact.contexts.identity.domain.session import Session
from jobact.contexts.identity.domain.user import User
from jobact.contexts.identity.infrastructure.membership_repository import (
    MembershipRepository,
)
from jobact.contexts.identity.infrastructure.organization_repository import (
    OrganizationRepository,
)
from jobact.contexts.identity.infrastructure.session_repository import SessionRepository
from jobact.contexts.identity.infrastructure.user_repository import UserRepository
from jobact.shared.application.ports import IdGenerator

SESSION_LIFETIME = timedelta(days=30)


@dataclass(frozen=True)
class AuthenticationResult:
    session_id: str
    user_id: UUID
    organization_id: UUID
    role: str


async def provision_personal_account(
    db_session: Any,
    *,
    user: User,
    workspace_name: str,
    now: datetime,
    id_generator: IdGenerator,
) -> AuthenticationResult:
    await UserRepository(db_session).add(user)
    organization = Organization(
        id=id_generator.new_id(), name=workspace_name, created_at=now
    )
    await OrganizationRepository(db_session).add(organization)
    membership = Membership(
        id=id_generator.new_id(),
        user_id=user.id,
        organization_id=organization.id,
        role="owner",
        joined_at=now,
        revoked_at=None,
    )
    await MembershipRepository(db_session).add(membership)
    return await create_session(
        db_session,
        user_id=user.id,
        organization_id=organization.id,
        role=membership.role,
        now=now,
        id_generator=id_generator,
    )


async def create_session_for_user(
    db_session: Any,
    *,
    user_id: UUID,
    now: datetime,
    id_generator: IdGenerator,
) -> AuthenticationResult:
    membership = await MembershipRepository(db_session).get_by_user_id(user_id)
    if membership is None or not membership.is_active:
        raise ValueError(f"user {user_id} has no active membership")
    return await create_session(
        db_session,
        user_id=user_id,
        organization_id=membership.organization_id,
        role=membership.role,
        now=now,
        id_generator=id_generator,
    )


async def create_session(
    db_session: Any,
    *,
    user_id: UUID,
    organization_id: UUID,
    role: str,
    now: datetime,
    id_generator: IdGenerator,
) -> AuthenticationResult:
    session = Session(
        id=str(id_generator.new_id()),
        user_id=user_id,
        organization_id=organization_id,
        device_id=None,
        created_at=now,
        last_seen_at=now,
        expires_at=now + SESSION_LIFETIME,
        revoked_at=None,
        ip=None,
        user_agent=None,
    )
    await SessionRepository(db_session).add(session)
    return AuthenticationResult(
        session_id=session.id,
        user_id=user_id,
        organization_id=organization_id,
        role=role,
    )
