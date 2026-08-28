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

from jobact.contexts.identity.domain.local_credential import normalize_email
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
        currency: str,
        timezone: str,
        registered_at: datetime,
        activated_at: datetime | None,
        last_seen_at: datetime,
        profile: UserProfile,
        linked_identities: list[LinkedIdentity] | None = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.email = normalize_email(email)
        self.email_verified = email_verified
        self.status = status
        self.locale = locale
        self.currency = currency
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
        currency: str,
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
            currency=currency,
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

    def change_locale(self, locale: str) -> None:
        if locale not in {"en-US", "ru-RU"}:
            raise ValueError("Unsupported locale")
        self.locale = locale

    def change_currency(self, currency: str) -> None:
        if currency not in {"USD", "RUB"}:
            raise ValueError("Unsupported currency")
        self.currency = currency

    def change_email(self, email: str, email_verified: bool) -> None:
        """Update this user's email (e.g. when a linked identity provider
        reports a new email on a later sign-in).
        """
        self.email = normalize_email(email)
        self.email_verified = email_verified

    def has_linked_identity(self, provider: str) -> bool:
        return any(linked.provider == provider for linked in self.linked_identities)
