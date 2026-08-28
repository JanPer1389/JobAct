"""Evidence-readiness invariant for a `Visit` -- whether enough real
evidence exists to start AI report analysis. Pure domain: `Visit`
cannot see `MediaAsset` rows itself (cross-aggregate), so callers pass
in pre-computed attached-photo counts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisitReadiness:
    has_customer: bool
    has_geolocation: bool
    has_before_photos: bool
    has_matching_after_photos: bool

    @property
    def is_ready(self) -> bool:
        return all(
            (
                self.has_customer,
                self.has_geolocation,
                self.has_before_photos,
                self.has_matching_after_photos,
            )
        )

    def missing_requirements(self) -> list[str]:
        missing: list[str] = []
        if not self.has_customer:
            missing.append("customer")
        if not self.has_geolocation:
            missing.append("geolocation")
        if not self.has_before_photos:
            missing.append("before_photos")
        if not self.has_matching_after_photos:
            missing.append("after_photos_matching_before")
        return missing
