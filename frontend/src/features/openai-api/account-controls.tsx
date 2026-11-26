import { useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { ProviderLogo } from "@/components/brand/provider-account-name";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useAccountColorHexes } from "@/features/accounts/account-colors";
import { OpenAIApiAccountDetail } from "./account-detail";
import type { OpenAIApiAccount } from "./api";
import { ModelPicker, type ModelPickerKind } from "./model-picker";
import { useOpenAIApi } from "./use-openai-api";

type Editing = { mode: "new" } | { mode: "key" | "credit"; account: OpenAIApiAccount };

const parseAmount = (value: string) => (value.trim() === "" ? null : Number(value));
const parseDay = (value: string) => (value.trim() === "" ? null : Number.parseInt(value, 10));

function CreditFields({
  amount,
  day,
  onAmount,
  onDay,
}: {
  amount: string;
  day: string;
  onAmount: (value: string) => void;
  onDay: (value: string) => void;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="block space-y-1 text-sm">
        Monthly credit (USD, optional)
        <Input
          type="number"
          min={0}
          step="0.01"
          inputMode="decimal"
          value={amount}
          onChange={(event) => onAmount(event.target.value)}
          placeholder="For the remaining-credit estimate"
        />
      </label>
      <label className="block space-y-1 text-sm">
        Renewal day (optional)
        <Input
          type="number"
          min={1}
          max={31}
          step={1}
          inputMode="numeric"
          value={day}
          onChange={(event) => onDay(event.target.value)}
          placeholder="1st of the month"
        />
      </label>
    </div>
  );
}

export function OpenAIApiAccountControls({
  readOnly = false,
  account,
  onCreated,
  children,
}: {
  readOnly?: boolean;
  account: OpenAIApiAccount | null;
  onCreated: (id: string) => void;
  children: (controls: { onAdd: () => void; detail: ReactNode }) => ReactNode;
}) {
  const { create, update, refresh, remove } = useOpenAIApi();
  const accountColors = useAccountColorHexes();
  const [editing, setEditing] = useState<Editing | null>(null);
  const [models, setModels] = useState<{ account: OpenAIApiAccount; kind: ModelPickerKind } | null>(null);
  const [deleting, setDeleting] = useState<OpenAIApiAccount | null>(null);
  const [name, setName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [amount, setAmount] = useState("");
  const [day, setDay] = useState("");
  const busy = create.isPending || update.isPending || refresh.isPending || remove.isPending;
  const error = create.error || update.error || refresh.error || remove.error;
  const open = (next: Editing) => {
    setEditing(next);
    setName("");
    setApiKey("");
    const state = next.mode === "new" ? null : next.account.state;
    setAmount(state?.monthly_credit_usd == null ? "" : String(state.monthly_credit_usd));
    setDay(state?.credit_renews_on == null ? "" : String(state.credit_renews_on));
  };
  const close = () => {
    setEditing(null);
    setApiKey("");
  };
  const submit = async () => {
    if (!editing) return;
    if (editing.mode === "new") {
      const monthlyCreditUsd = parseAmount(amount);
      const creditRenewsOn = parseDay(day);
      const created = await create.mutateAsync({
        name,
        apiKey,
        ...(monthlyCreditUsd === null ? {} : { monthlyCreditUsd }),
        ...(creditRenewsOn === null ? {} : { creditRenewsOn }),
      });
      onCreated(created.id);
    } else if (editing.mode === "key") {
      await update.mutateAsync({ id: editing.account.id, body: { apiKey } });
    } else {
      await update.mutateAsync({
        id: editing.account.id,
        body: { monthlyCreditUsd: parseAmount(amount), creditRenewsOn: parseDay(day) },
      });
    }
    close();
  };
  const title =
    editing?.mode === "new" ? "Add OpenAI API account" : editing?.mode === "key" ? "Replace API key" : "Monthly credit";
  const formError = create.error || update.error;
  const canSubmit =
    editing?.mode === "new" ? !!name.trim() && !!apiKey : editing?.mode === "key" ? !!apiKey : true;
  return (
    <>
      {children({
        onAdd: () => open({ mode: "new" }),
        detail: account ? (
          <OpenAIApiAccountDetail
            account={account}
            color={accountColors.modelSources.get(account.id)}
            readOnly={readOnly}
            busy={busy}
            error={error?.message}
            onKey={() => open({ mode: "key", account })}
            onCredit={() => open({ mode: "credit", account })}
            onRename={(name) => update.mutateAsync({ id: account.id, body: { name } })}
            onModels={() => setModels({ account, kind: "text" })}
            onImageModels={() => setModels({ account, kind: "image" })}
            onRefresh={() => refresh.mutate(account.id)}
            onToggle={(isEnabled) => update.mutate({ id: account.id, body: { isEnabled } })}
            onDelete={() => setDeleting(account)}
            onRoutingPolicy={(routingPolicy) => update.mutate({ id: account.id, body: { routingPolicy } })}
          />
        ) : null,
      })}
      {models && (
        <ModelPicker
          key={models.account.id + models.kind}
          account={models.account}
          kind={models.kind}
          busy={busy}
          onClose={() => setModels(null)}
          onSave={(selections) =>
            update.mutateAsync({ id: models.account.id, body: { selections } }).then(() => undefined)
          }
        />
      )}
      <Dialog
        open={editing !== null}
        onOpenChange={(next) => {
          if (!next) close();
        }}
      >
        <DialogContent className="max-h-[90dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ProviderLogo provider="openai_apikey" />
              {title}
            </DialogTitle>
            <DialogDescription>
              {editing?.mode === "credit"
                ? "The estimate subtracts spend recorded by codex-lb since the last renewal. Leave the amount empty to show spend only."
                : "A Platform project key for api.openai.com. It is encrypted and serves /v1 clients and image models, never Codex."}
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={async (event) => {
              event.preventDefault();
              try {
                await submit();
              } catch {
                /* Mutation error is displayed below. */
              }
            }}
          >
            {editing?.mode === "new" && (
              <label className="block space-y-1 text-sm">
                Name
                <Input required value={name} onChange={(event) => setName(event.target.value)} />
              </label>
            )}
            {editing?.mode !== "credit" && (
              <label className="block space-y-1 text-sm">
                API key
                <Input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                />
              </label>
            )}
            {editing?.mode !== "key" && <CreditFields amount={amount} day={day} onAmount={setAmount} onDay={setDay} />}
            {formError && (
              <p role="alert" className="text-sm text-destructive">
                {formError.message}
              </p>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" disabled={busy} onClick={close}>
                Cancel
              </Button>
              <Button type="submit" disabled={readOnly || busy || !canSubmit}>
                {editing?.mode === "new" ? "Add account" : "Save"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(next) => {
          if (!next) setDeleting(null);
        }}
        title="Delete OpenAI API account?"
        description="The account and its model routes will be removed. Request history remains."
        confirmLabel="Delete"
        confirmDisabled={remove.isPending}
        onConfirm={async () => {
          if (deleting) {
            await remove.mutateAsync(deleting.id);
            setDeleting(null);
          }
        }}
      />
    </>
  );
}
