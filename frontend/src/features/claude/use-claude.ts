import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export function useClaudeAccounts() {
  return useQuery({
    queryKey: ["claude-accounts"],
    queryFn: api.listAccounts,
    refetchInterval: 60000,
  });
}

export function useClaude() {
  const client = useQueryClient();
  const invalidate = async () => {
    await Promise.all(
      ["claude-accounts", "model-sources", "models"].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    );
  };
  const enroll = useMutation({
    mutationFn: api.importAccount,
    onSuccess: invalidate,
  });
  const start = useMutation({ mutationFn: api.startOAuth });
  const reconnect = useMutation({
    mutationFn: ({ id, credentials }: { id: string; credentials: unknown }) =>
      api.reconnectAccount(id, {
        credentials,
        acknowledgeExclusiveRefresh: true,
      }),
    onSuccess: invalidate,
  });
  const complete = useMutation({
    mutationFn: api.completeOAuth,
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: api.ClaudeUpdate }) =>
      api.updateAccount(id, body),
    onSuccess: invalidate,
  });
  const refresh = useMutation({
    mutationFn: api.refreshAccount,
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: api.deleteAccount,
    onSuccess: invalidate,
  });
  return { enroll, reconnect, start, complete, update, refresh, remove };
}
