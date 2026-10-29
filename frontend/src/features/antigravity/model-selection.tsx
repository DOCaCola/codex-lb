import { AccountModelPicker } from "@/features/accounts/components/account-model-picker";
import type { AntigravityAccount, AntigravityUpdate } from "./api";
import { FAMILY_LABELS } from "./display-values";

export function AntigravityModelSelection({
  account,
  readOnly,
  onSave,
  onClose,
}: {
  account: AntigravityAccount;
  readOnly: boolean;
  onSave: (settings: AntigravityUpdate) => Promise<unknown>;
  onClose: () => void;
}) {
  return (
    <AccountModelPicker
      name={account.name}
      provider="Antigravity"
      allModels={account.state.all_models}
      reasoningRestrictions={{}}
      selectedModels={account.state.selections}
      disabled={readOnly}
      onClose={onClose}
      onSave={(models, allModels) => onSave({ selections: models, allModels })}
      catalog={account.state.catalog.map((family) => {
        const tiers = Object.keys(family.tiers);
        return {
          model: family.id,
          name: family.display_name,
          available: true,
          // Effort tiers are separate upstream models; the client's reasoning effort selects one.
          reasoningLevels: [],
          description:
            FAMILY_LABELS[family.quota_family] + " quota" + (tiers.length ? " · effort tiers: " + tiers.join(", ") : ""),
        };
      })}
    />
  );
}
