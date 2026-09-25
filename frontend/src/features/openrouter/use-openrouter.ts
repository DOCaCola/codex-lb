import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAccount,
  deleteAccount,
  listAccounts,
  refreshAccount,
  updateAccount,
  type AccountUpdate,
} from "./api";

export function useOpenRouter() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["openrouter-accounts"],
    queryFn: listAccounts,
    refetchInterval: 60000,
  });
  const invalidate = async () => {
    await Promise.all(
      ["openrouter-accounts", "model-sources", "models"].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    );
  };
  const create = useMutation({
    mutationFn: createAccount,
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: AccountUpdate }) =>
      updateAccount(id, body),
    onSuccess: invalidate,
  });
  const refresh = useMutation({
    mutationFn: refreshAccount,
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: deleteAccount,
    onSuccess: invalidate,
  });
  return { query, create, update, refresh, remove };
}
