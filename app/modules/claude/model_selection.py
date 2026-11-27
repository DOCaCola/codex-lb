from app.modules.claude.schemas import AccountState, ModelSelection


def publishable_text_models(state: AccountState) -> dict[str, str]:
    """Every servable catalog model under its published slug, enabled or not."""
    return {f"anthropic/{model.id}": model.display_name for model in state.catalog if model.token_limits is not None}


def effective_selections(state: AccountState) -> list[ModelSelection]:
    selections = {selection.model: selection for selection in state.selections}
    if state.all_models:
        for model in state.catalog:
            if model.token_limits is not None:
                selections.setdefault(model.id, ModelSelection(model=model.id))
        for model in state.reasoning_restrictions:
            selections.setdefault(model, ModelSelection(model=model))
    return list(selections.values())
