import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export function useAntigravityAccounts() {
  return useQuery({
    queryKey: ["antigravity-accounts"],
    queryFn: api.listAccounts,
    refetchInterval: 60000,
  });
}

export function useAntigravity() {
  const client = useQueryClient();
  const invalidate = async () => {
    await Promise.all(
      ["antigravity-accounts", "model-sources", "models", "account-colors"].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    );
  };
  const enroll = useMutation({ mutationFn: api.importAccount, onSuccess: invalidate });
  const start = useMutation({ mutationFn: api.startOAuth });
  const complete = useMutation({ mutationFn: api.completeOAuth, onSuccess: invalidate });
  const reconnect = useMutation({
    mutationFn: ({ id, credentials }: { id: string; credentials: unknown }) =>
      api.reconnectAccount(id, { credentials }),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: api.AntigravityUpdate }) => api.updateAccount(id, body),
    onSuccess: invalidate,
  });
  const refresh = useMutation({ mutationFn: api.refreshAccount, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: api.deleteAccount, onSuccess: invalidate });
  return { enroll, start, complete, reconnect, update, refresh, remove };
}
