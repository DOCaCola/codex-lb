from app.modules.claude.schemas import AccountState, ModelSelection


def effective_selections(state: AccountState) -> list[ModelSelection]:
    selections = {selection.model: selection for selection in state.selections}
    if state.all_models:
        for model in state.catalog:
            if model.token_limits is not None:
                selections.setdefault(model.id, ModelSelection(model=model.id))
    return list(selections.values())
