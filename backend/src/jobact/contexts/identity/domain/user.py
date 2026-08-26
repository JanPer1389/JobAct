"""`User` aggregate: an authenticated person, with their linked external
identities and profile nested inside as value data.

`LinkedIdentity`/`UserProfile` have no independent lifecycle apart from
their owning `User` (they get their own tables for storage normalization,
but never their own aggregate/repository), so they live inside this
aggregate rather than as separate `AggregateRoot`s -- unlike `Membership`
and `Session`, which need independent, cheap lookup.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from jobact.shared.domain import AggregateRoot


@dataclass(frozen=True)
class UserProfile:
    display_name: str
    given_name: str
    family_name: str
    avatar_url: str | None


@dataclass(frozen=True)
class LinkedIdentity:
    provider: str
    provider_subject: str


class User(AggregateRoot):
    """A registered user, identified by email, with zero or more linked
    external (OIDC) identities and a profile.
    """

    def __init__(
        self,
        *,
        id: UUID,
        email: str,
        email_verified: bool,
        status: str,
        locale: str,
        timezone: str,
        registered_at: datetime,
        activated_at: datetime | None,
        last_seen_at: datetime,
        profile: UserProfile,
        linked_identities: list[LinkedIdentity] | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.email = email
        self.email_verified = email_verified
        self.status = status
        self.locale = locale
        self.timezone = timezone
        self.registered_at = registered_at
        self.activated_at = activated_at
        self.last_seen_at = last_seen_at
        self.profile = profile
        self.linked_identities = list(linked_identities) if linked_identities else []

    @classmethod
    def register(
        cls,
        *,
        id: UUID,
        email: str,
        email_verified: bool,
        display_name: str,
        given_name: str,
        family_name: str,
        avatar_url: str | None,
        locale: str,
        timezone: str,
        registered_at: datetime,
    ) -> "User":
        """Construct a brand-new `User` from external-identity-shaped
        input (e.g. Task 1.2's Google OIDC `ExternalIdentity`), before any
        provider has actually been linked.

        `activated_at` is left `None` until the user's first real use
        (whatever a later task decides that means); `last_seen_at`
        defaults to `registered_at`.
        """
        return cls(
            id=id,
            email=email,
            email_verified=email_verified,
            status="active",
            locale=locale,
            timezone=timezone,
            registered_at=registered_at,
            activated_at=None,
            last_seen_at=registered_at,
            profile=UserProfile(
                display_name=display_name,
                given_name=given_name,
                family_name=family_name,
                avatar_url=avatar_url,
            ),
            linked_identities=[],
        )

    def link_identity(self, provider: str, provider_subject: str) -> None:
        """Link an external identity to this user. Idempotent: linking
        the same `(provider, provider_subject)` pair twice does not
        duplicate the list entry.
        """
        for linked in self.linked_identities:
            if (
                linked.provider == provider
                and linked.provider_subject == provider_subject
            ):
                return
        self.linked_identities.append(
            LinkedIdentity(provider=provider, provider_subject=provider_subject)
        )

    def touch_last_seen(self, now: datetime) -> None:
        self.last_seen_at = now
