"""Fields of the Codex ``x-codex-turn-metadata`` JSON that codex-lb reads."""

import json

from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_mapping

COMPOSER_PREDICTIONS_THREAD_SOURCE = "composer_predictions"


def codex_turn_thread_source(raw_turn_metadata: JsonValue | None) -> str | None:
    """The ``thread_source`` a Codex turn declares, e.g. a desktop prediction fork.

    Codex sends the turn metadata as a JSON string: the ``x-codex-turn-metadata``
    header over HTTP and the same key inside ``client_metadata`` over WebSocket.
    """
    if not isinstance(raw_turn_metadata, str):
        return None
    try:
        turn_metadata = json.loads(raw_turn_metadata)
    except json.JSONDecodeError:
        return None
    if not is_json_mapping(turn_metadata):
        return None
    thread_source = turn_metadata.get("thread_source")
    return thread_source if isinstance(thread_source, str) else None


def is_composer_prediction_turn(raw_turn_metadata: JsonValue | None) -> bool:
    return codex_turn_thread_source(raw_turn_metadata) == COMPOSER_PREDICTIONS_THREAD_SOURCE
