import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { get, put } from "@/lib/api-client";
import type { AccountColorTarget } from "@/features/accounts/account-colors";

export const ACCOUNT_NOTE_MAX_LENGTH = 2000;

export const ACCOUNT_NOTES_QUERY_KEY = ["account-notes"] as const;

const AccountNoteSchema = z.object({
  accountId: z.string().nullable(),
  modelSourceId: z.string().nullable(),
  note: z.string(),
});

const AccountNotesResponseSchema = z.object({
  notes: z.array(AccountNoteSchema),
});

export type AccountNote = z.infer<typeof AccountNoteSchema>;

/** A Codex account, or a model source (Claude, Antigravity, OpenRouter and other provider accounts). */
export type AccountNoteTarget = AccountColorTarget;

export function findAccountNote(notes: AccountNote[] | undefined, target: AccountNoteTarget): string | null {
  const entry = notes?.find((note) =>
    "accountId" in target ? note.accountId === target.accountId : note.modelSourceId === target.modelSourceId,
  );
  return entry?.note ?? null;
}

export function useAccountNotes() {
  return useQuery({
    queryKey: ACCOUNT_NOTES_QUERY_KEY,
    queryFn: () => get("/api/account-notes", AccountNotesResponseSchema),
    select: (data) => data.notes,
  });
}

export function useSetAccountNote(target: AccountNoteTarget) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const path =
    "accountId" in target
      ? `/api/account-notes/accounts/${encodeURIComponent(target.accountId)}`
      : `/api/account-notes/model-sources/${encodeURIComponent(target.modelSourceId)}`;
  return useMutation({
    mutationFn: (note: string | null) => put(path, AccountNotesResponseSchema, { body: { note } }),
    onSuccess: (data) => {
      client.setQueryData(ACCOUNT_NOTES_QUERY_KEY, data);
    },
    onError: (error: Error) => {
      toast.error(error.message || t("accounts.toasts.noteUpdateFailed"));
    },
  });
}
