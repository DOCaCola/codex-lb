import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { consumeGrant, readGrants, type ResetRequest } from "./reset-api";

const windowLabel = (name: string) =>
  ({
    five_hour: "5-hour",
    seven_day: "Weekly",
    seven_day_overage_included: "Model overage",
  })[name] ?? name;

export function ClaudeResetGrants({
  accountId,
  readOnly,
}: {
  accountId: string;
  readOnly: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState<ResetRequest | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [uncertain, setUncertain] = useState<ResetRequest | null>(null);
  const [acknowledge, setAcknowledge] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["claude-reset-grants", accountId],
    queryFn: () => readGrants(accountId),
    enabled: open,
    retry: false,
  });
  useEffect(() => {
    if (!open) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [open]);
  const pending = query.data?.operations.filter((op) => !op.result) ?? [];
  const active = pending.some((op) => Date.parse(op.retryUntil) > now);
  const expired = pending.some((op) => Date.parse(op.retryUntil) <= now);
  const blocked = busy || readOnly || query.isFetching;
  const status = query.data?.status;
  const untracked =
    uncertain &&
    !query.data?.operations.some(
      (op) => op.operationId === uncertain.operationId,
    )
      ? uncertain
      : null;

  async function spend(request: ResetRequest) {
    setConfirm(null);
    setBusy(true);
    setMessage("");
    // Keep the ID even if the browser loses the server's settled answer.
    setUncertain(request);
    try {
      const response = await consumeGrant(accountId, request);
      if (response.operation.result) {
        setUncertain(null);
        setMessage(
          `Reset result: ${response.operation.result.result.replaceAll("_", " ")}.${
            response.operation.result.result === "reset" &&
            !response.refreshComplete
              ? " Redemption is confirmed; usage refresh is pending. Do not spend again to refresh usage."
              : ""
          }`,
        );
      } else {
        setMessage(
          "Outcome unknown. Retry the same operation; do not start another spend.",
        );
      }
    } catch {
      setMessage(
        "No confirmed result received. Refresh status or retry the same operation; it may have been sent.",
      );
    } finally {
      setBusy(false);
      void query.refetch();
      void client.invalidateQueries({ queryKey: ["claude-accounts"] });
    }
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Ticket className="h-4 w-4" /> Reset grants
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Claude reset grants</DialogTitle>
            <DialogDescription>
              Manually spend an available grant. Only the listed usage windows
              are reset. Nothing is spent automatically.
            </DialogDescription>
          </DialogHeader>
          <Button
            variant="outline"
            size="sm"
            disabled={busy || query.isFetching}
            onClick={() => void query.refetch()}
          >
            Refresh status
          </Button>
          {query.isLoading && <p role="status">Loading grants…</p>}
          {(query.error || query.data?.error) && (
            <p role="alert" className="text-sm text-destructive">
              {query.data?.error ??
                "Could not load reset grants. No balance is assumed."}
            </p>
          )}
          {message && (
            <p role="status" className="text-sm">
              {message}
            </p>
          )}
          {status && !status.eligible && (
            <p className="text-sm">
              This account is not currently eligible for reset grants.
            </p>
          )}
          {status?.grants.length === 0 && (
            <p className="text-sm">No reset grants available.</p>
          )}
          {pending.map((operation) => (
            <div
              key={operation.operationId}
              className="rounded-lg border p-3 space-y-2"
            >
              <p className="text-sm">Uncertain reset: {operation.grantId}</p>
              <p className="text-xs text-muted-foreground">
                {Date.parse(operation.retryUntil) <= now
                  ? "The same-ID retry window expired. The earlier reset may have been spent."
                  : "Retry uses the original operation ID and cannot start a new spend."}
              </p>
              <Button
                variant="outline"
                size="sm"
                disabled={
                  blocked ||
                  Date.parse(operation.retryUntil) <= now ||
                  Date.parse(operation.leaseUntil) > now
                }
                onClick={() =>
                  void spend({
                    grantId: operation.grantId,
                    operationId: operation.operationId,
                    confirmed: true,
                    acknowledgeUncertain: false,
                  })
                }
              >
                Retry same operation
              </Button>
            </div>
          ))}
          {untracked && (
            <Button
              variant="outline"
              disabled={blocked}
              onClick={() => void spend(untracked)}
            >
              Recover last operation
            </Button>
          )}
          {expired && (
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={acknowledge}
                disabled={blocked}
                onChange={(e) => setAcknowledge(e.target.checked)}
              />
              I understand an earlier outcome is unknown and a new operation
              could spend another reset.
            </label>
          )}
          {status?.grants.map((grant) => {
            const usable =
              status.eligible &&
              grant.usable_now &&
              !grant.paused &&
              grant.resets_left > 0 &&
              (!grant.use_requires_limit || status.at_limit) &&
              (!grant.starts_at || Date.parse(grant.starts_at) <= now) &&
              (!grant.ends_at || Date.parse(grant.ends_at) > now) &&
              (!status.cooldown_until ||
                Date.parse(status.cooldown_until) <= now);
            return (
              <div key={grant.id} className="rounded-lg border p-3 space-y-2">
                <p className="font-medium">{grant.label || grant.id}</p>
                <p className="text-sm tabular-nums">
                  {grant.resets_left} of {grant.resets_total} resets remaining
                </p>
                <p className="text-sm text-muted-foreground">
                  Clears:{" "}
                  {grant.clears.map(windowLabel).join(", ") || "Not specified"}
                </p>
                {grant.ends_at && (
                  <p className="text-xs text-muted-foreground">
                    Expires {new Date(grant.ends_at).toLocaleString()}
                  </p>
                )}
                <Button
                  size="sm"
                  disabled={
                    blocked ||
                    !usable ||
                    active ||
                    !!untracked ||
                    (expired && !acknowledge)
                  }
                  onClick={() =>
                    setConfirm({
                      grantId: grant.id,
                      operationId: crypto.randomUUID(),
                      confirmed: true,
                      acknowledgeUncertain: acknowledge,
                    })
                  }
                >
                  Redeem grant
                </Button>
              </div>
            );
          })}
          {query.data?.operations
            .filter((op) => op.result)
            .slice(0, 3)
            .map((op) => (
              <p className="text-xs text-muted-foreground" key={op.operationId}>
                {op.grantId}: {op.result?.result.replaceAll("_", " ")}
              </p>
            ))}
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={!!confirm}
        onOpenChange={(value) => {
          if (!value) setConfirm(null);
        }}
        title="Spend this reset grant?"
        description="This consumes a subscription benefit. Only the grant’s listed windows are cleared. This cannot be undone."
        confirmLabel="Confirm redemption"
        confirmDisabled={blocked}
        onConfirm={() => {
          if (confirm) void spend(confirm);
        }}
      />
    </>
  );
}
