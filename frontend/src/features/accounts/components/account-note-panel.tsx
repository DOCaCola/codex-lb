import { Pencil } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  ACCOUNT_NOTE_MAX_LENGTH,
  findAccountNote,
  useAccountNotes,
  useSetAccountNote,
  type AccountNoteTarget,
} from "@/features/accounts/account-notes";

/** Free-text operator note shown under the header of every account detail. */
export function AccountNotePanel({ target, readOnly }: { target: AccountNoteTarget; readOnly: boolean }) {
  const { t } = useTranslation();
  const { data: notes } = useAccountNotes();
  const setNote = useSetAccountNote(target);
  const note = findAccountNote(notes, target);
  const [draft, setDraft] = useState<string | null>(null);
  const editing = draft !== null;

  const save = async () => {
    if (draft === null) return;
    try {
      await setNote.mutateAsync(draft.trim() === "" ? null : draft);
    } catch {
      return; // Stay in edit mode; the mutation reports the error.
    }
    setDraft(null);
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[13px] font-medium">
          {t("accounts.detail.note.title")}
        </h3>
        {!readOnly && !editing ? (
          <Button
            type="button"
            size="icon-xs"
            variant="ghost"
            className="text-muted-foreground"
            aria-label={t("accounts.detail.note.edit")}
            title={t("accounts.detail.note.edit")}
            onClick={() => setDraft(note ?? "")}
          >
            <Pencil className="h-3 w-3" />
          </Button>
        ) : null}
      </div>
      {editing ? (
        <div className="space-y-2">
          <textarea
            aria-label={t("accounts.detail.note.label")}
            className="border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 min-h-20 w-full rounded-md border bg-transparent px-3 py-2 text-xs shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px]"
            maxLength={ACCOUNT_NOTE_MAX_LENGTH}
            placeholder={t("accounts.detail.note.placeholder")}
            value={draft}
            autoFocus
            disabled={setNote.isPending}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                setDraft(null);
              }
            }}
          />
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="outline" className="h-7 text-xs" onClick={() => setDraft(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="button"
              size="sm"
              className="h-7 text-xs"
              disabled={setNote.isPending}
              onClick={() => void save()}
            >
              {t("common.actions.save")}
            </Button>
          </div>
        </div>
      ) : note ? (
        <p className="whitespace-pre-wrap break-words text-xs">{note}</p>
      ) : (
        <p className="text-xs text-muted-foreground">{t("accounts.detail.note.empty")}</p>
      )}
    </div>
  );
}
