import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAccount,
  deleteAccount,
  listAccounts,
  refreshAccount,
  updateAccount,
  type AccountUpdate,
} from "./api";

export function useOpenAIApiAccounts() {
  return useQuery({
    queryKey: ["openai-api-accounts"],
    queryFn: listAccounts,
    refetchInterval: 60000,
  });
}

export function useOpenAIApi() {
  const client = useQueryClient();
  const query = useOpenAIApiAccounts();
  const invalidate = async () => {
    await Promise.all(
      ["openai-api-accounts", "model-sources", "models", "account-colors"].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    );
  };
  const create = useMutation({ mutationFn: createAccount, onSuccess: invalidate });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: AccountUpdate }) => updateAccount(id, body),
    onSuccess: invalidate,
  });
  const refresh = useMutation({ mutationFn: refreshAccount, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: deleteAccount, onSuccess: invalidate });
  return { query, create, update, refresh, remove };
}
