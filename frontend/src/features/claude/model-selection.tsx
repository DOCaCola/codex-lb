import { AccountModelPicker } from "@/features/accounts/components/account-model-picker";
import { formatCompactNumber } from "@/utils/formatters";
import type { ClaudeAccount, ClaudeSelection } from "./api";

export function ModelSelection({
  account,
  readOnly,
  onSave,
  onClose,
}: {
  account: ClaudeAccount;
  readOnly: boolean;
  onSave: (selections: ClaudeSelection[]) => Promise<unknown>;
  onClose: () => void;
}) {
  return (
    <AccountModelPicker
      name={account.name}
      provider="Claude"
      selectedModels={account.state.selections.map(
        (selection) => selection.model,
      )}
      disabled={readOnly}
      onClose={onClose}
      onSave={(models) => onSave(models.map((model) => ({ model })))}
      catalog={account.state.catalog.map((model) => ({
        model: model.id,
        name: model.display_name,
        available: model.max_input_tokens !== null && model.max_tokens !== null,
        description:
          model.max_input_tokens !== null && model.max_tokens !== null
            ? `${formatCompactNumber(model.max_input_tokens)} context · ${formatCompactNumber(model.max_tokens)} maximum output · ${formatCompactNumber(Math.min(64000, model.max_tokens))} default output`
            : "Token limits unavailable. Refresh the catalog before enabling this model.",
      }))}
    />
  );
}
