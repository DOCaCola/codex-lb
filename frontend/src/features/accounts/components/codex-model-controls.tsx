import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Layers } from "lucide-react";
import {
  getAccountModelSettings,
  updateAccountModels,
} from "@/features/accounts/api";
import type { AccountModelSelectionRequest } from "@/features/accounts/schemas";
import { Button } from "@/components/ui/button";
import { formatCompactNumber } from "@/utils/formatters";
import { AccountModelPicker } from "./account-model-picker";

export function CodexModelControls({
  accountId,
  name,
  disabled,
  children,
}: {
  accountId: string;
  name: string;
  disabled: boolean;
  children: (controls: { mode: ReactNode; action: ReactNode }) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["accounts", "models", accountId],
    queryFn: ({ signal }) => getAccountModelSettings(accountId, { signal }),
  });
  const update = useMutation({
    mutationFn: (body: AccountModelSelectionRequest) =>
      updateAccountModels(accountId, body),
    onSuccess: async (data) => {
      queryClient.setQueryData(["accounts", "models", accountId], data);
      await queryClient.invalidateQueries({ queryKey: ["accounts", "list"] });
    },
  });
  if (!query.data)
    return children({
      mode: (
        <p
          role={query.isError ? "alert" : "status"}
          className="text-xs text-muted-foreground"
        >
          {query.isError
            ? "Unable to load model settings."
            : "Loading model settings…"}
          {query.isError && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => void query.refetch()}
            >
              Retry
            </Button>
          )}
        </p>
      ),
      action: null,
    });
  const data = query.data;
  return (
    <>
      {children({
        mode: null,
        action: (
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={disabled || update.isPending}
            onClick={() => setOpen(true)}
          >
            <Layers className="h-3.5 w-3.5" />
            Models ({data.allModels ? "All" : data.selectedModels.length})
          </Button>
        ),
      })}
      {open && (
        <AccountModelPicker
          name={name}
          provider="Codex"
          selectedModels={data.selectedModels}
          allModels={data.allModels}
          reasoningRestrictions={data.reasoningRestrictions}
          disabled={disabled || update.isPending}
          catalog={data.catalog.map((model) => ({
            model: model.model,
            name: model.displayName,
            available: model.available,
            reasoningLevels: model.reasoningLevels,
            description: [
              `${formatCompactNumber(model.contextWindow)} context`,
              model.supportsTools ? "Tools" : "",
              model.supportsVision ? "Vision" : "",
              model.supportsReasoning ? "Reasoning" : "",
            ]
              .filter(Boolean)
              .join(" · "),
          }))}
          onClose={() => setOpen(false)}
          onSave={(selectedModels, allModels, reasoningRestrictions) =>
            update.mutateAsync({
              allModels,
              selectedModels,
              reasoningRestrictions,
            })
          }
        />
      )}
    </>
  );
}
