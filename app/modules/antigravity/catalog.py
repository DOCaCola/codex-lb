"""fetchAvailableModels -> client-facing model families with effort tiers."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.types import JsonValue
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.schemas import EFFORTS, CatalogFamily, Effort, ModelQuotaReading, QuotaFamily

_TIERED = re.compile(r"^(?P<family>.+)-(?P<effort>low|medium|high)$")
_DISPLAY_TIER = re.compile(r"\s*\((?:low|medium|high)\)\s*$", re.IGNORECASE)
_ARGON = re.compile(r"argon|gemini[-_\s]*4\b", re.IGNORECASE)


class QuotaInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    remaining_fraction: float | None = Field(default=None, alias="remainingFraction")
    reset_time: datetime | None = Field(default=None, alias="resetTime")


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display_name: str | None = Field(default=None, alias="displayName")
    model: str | None = None
    api_provider: str | None = Field(default=None, alias="apiProvider")
    max_tokens: int | None = Field(default=None, gt=0, alias="maxTokens")
    max_output_tokens: int | None = Field(default=None, gt=0, alias="maxOutputTokens")
    supports_thinking: bool = Field(default=False, alias="supportsThinking")
    supports_images: bool = Field(default=False, alias="supportsImages")
    quota_info: QuotaInfo | None = Field(default=None, alias="quotaInfo")


def quota_family(model_id: str, display_name: str | None) -> QuotaFamily:
    """Argon first, then Gemini, then the Claude & GPT group (opencodex quota/antigravity.ts)."""
    text = f"{model_id} {display_name or ''}"
    if _ARGON.search(text):
        return "argon"
    if model_id.lower().startswith("gemini") or "gemini" in (display_name or "").lower():
        return "gemini"
    return "claude"


def _agent_models(data: dict[str, JsonValue]) -> list[str] | None:
    """The model IDs of the CLI's agent picker, in its order; None when the catalog has no sorts."""
    sorts = data.get("agentModelSorts")
    if not isinstance(sorts, list) or not sorts:
        return None
    ordered: list[str] = []
    for sort in sorts:
        groups = sort.get("groups") if isinstance(sort, dict) else None
        for group in groups if isinstance(groups, list) else []:
            ids = group.get("modelIds") if isinstance(group, dict) else None
            for model_id in ids if isinstance(ids, list) else []:
                if isinstance(model_id, str) and model_id not in ordered:
                    ordered.append(model_id)
    return ordered


def parse_catalog(data: dict[str, JsonValue]) -> tuple[list[CatalogFamily], str | None]:
    raw_models = data.get("models")
    if not isinstance(raw_models, dict):
        raise AntigravityError("Antigravity returned no model catalog", status_code=502)
    entries: dict[str, CatalogEntry] = {}
    for model_id, raw in raw_models.items():
        try:
            entries[model_id] = CatalogEntry.model_validate(raw)
        except ValidationError:
            continue
    offered = _agent_models(data)
    order = [model_id for model_id in (offered if offered is not None else sorted(entries)) if model_id in entries]
    families: dict[str, CatalogFamily] = {}
    for model_id in order:
        entry = entries[model_id]
        match = _TIERED.match(model_id)
        family_id = match.group("family") if match else model_id
        effort = cast(Effort, match.group("effort")) if match else None
        display = _DISPLAY_TIER.sub("", entry.display_name or family_id) or family_id
        family = families.get(family_id)
        if family is None:
            family = CatalogFamily(
                id=family_id,
                display_name=display,
                api_provider=entry.api_provider,
                quota_family=quota_family(model_id, entry.display_name),
                context_window=entry.max_tokens,
                max_output_tokens=entry.max_output_tokens,
                supports_images=entry.supports_images,
                supports_thinking=entry.supports_thinking,
            )
            families[family_id] = family
        elif family.api_provider != entry.api_provider:
            raise AntigravityError(f"Antigravity model family {family_id} mixes providers", status_code=502)
        else:
            # Tiers of one family share limits; keep the smallest so every tier fits.
            family.context_window = _smallest(family.context_window, entry.max_tokens)
            family.max_output_tokens = _smallest(family.max_output_tokens, entry.max_output_tokens)
            family.supports_images = family.supports_images and entry.supports_images
            family.supports_thinking = family.supports_thinking or entry.supports_thinking
        if effort is not None:
            family.tiers[effort] = model_id
        if entry.model:
            family.model_enums[model_id] = entry.model
        if entry.quota_info is not None and entry.quota_info.remaining_fraction is not None:
            reset = entry.quota_info.reset_time
            family.model_quota[model_id] = ModelQuotaReading(
                remaining_fraction=min(1.0, max(0.0, entry.quota_info.remaining_fraction)),
                resets_at=reset.astimezone(UTC) if reset is not None and reset.tzinfo else None,
            )
    for family in families.values():
        # A family seen only through an untiered ID is a standalone wire model.
        if family.tiers and family.id in entries:
            raise AntigravityError(f"Antigravity model {family.id} is both tiered and standalone", status_code=502)
    default = data.get("defaultAgentModelId")
    default_family = None
    if isinstance(default, str):
        match = _TIERED.match(default)
        default_family = match.group("family") if match else default
    return list(families.values()), default_family if default_family in families else None


def _smallest(current: int | None, value: int | None) -> int | None:
    if current is None or value is None:
        return current if value is None else value
    return min(current, value)


def search_model(data: dict[str, JsonValue]) -> str | None:
    """The model the CLI runs search_web on: the first webSearchModelIds entry, else the Flash Lite tier.

    Mock captures of agy 1.4.10: without tieredModelIds.flashLite the CLI fails every search
    ("failed to resolve Flash Lite model from TieredModelIDs"), even when webSearchModelIds is set.
    """
    tiered = data.get("tieredModelIds")
    flash_lite = tiered.get("flashLite") if isinstance(tiered, dict) else None
    if not isinstance(flash_lite, list) or not flash_lite or not isinstance(flash_lite[0], str):
        return None
    preferred = data.get("webSearchModelIds")
    if isinstance(preferred, list) and preferred and isinstance(preferred[0], str):
        return preferred[0]
    return flash_lite[0]


def levels(family: CatalogFamily) -> list[Effort]:
    return [level for level in EFFORTS if level in family.tiers]


def default_level(family: CatalogFamily) -> Effort | None:
    """The highest tier, as the CLI's default agent model (gemini-3.8-flash-high) is."""
    available = levels(family)
    return available[-1] if available else None


def wire_model(family: CatalogFamily, effort: str | None) -> tuple[str, Effort | None]:
    """The tiered wire ID for an effort: the nearest level this family advertises (opencodex c2f3d8b42)."""
    available = levels(family)
    if not available:
        return family.id, None
    if effort is None:
        chosen = available[-1]
    elif effort in ("xhigh", "max"):
        chosen = available[-1]
    elif effort in ("none", "minimal"):
        chosen = available[0]
    elif effort in EFFORTS:
        rank = EFFORTS.index(effort)
        # Nearest advertised level; a tie prefers the higher one.
        chosen = min(available, key=lambda level: (abs(EFFORTS.index(level) - rank), -EFFORTS.index(level)))
    else:
        raise AntigravityError(f"Unsupported reasoning effort: {effort}")
    return family.tiers[chosen], chosen
