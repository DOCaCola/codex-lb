import { Check, Pencil, X } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export type AccountNameEditorProps = {
  /** Heading content shown while not editing. */
  children: ReactNode;
  /** Initial draft when editing starts. */
  value: string;
  labels: { edit: string; input: string; save: string; cancel: string };
  inputId?: string;
  placeholder?: string;
  help?: string;
  /** Saving an empty draft sends null (clears the name) instead of being blocked. */
  allowEmpty?: boolean;
  /** Extra heading controls shown after the rename button while not editing. */
  accessory?: ReactNode;
  disabled: boolean;
  onSave: (value: string | null) => Promise<unknown>;
};

/** Account detail heading with the inline pencil rename shared by every provider. */
export function AccountNameEditor({
  children,
  value,
  labels,
  inputId,
  placeholder,
  help,
  allowEmpty = false,
  accessory,
  disabled,
  onSave,
}: AccountNameEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const trimmed = draft.trim();
  const saveBlocked = disabled || (!allowEmpty && trimmed === "");

  const handleSave = async () => {
    if (saveBlocked) return;
    try {
      await onSave(trimmed === "" ? null : trimmed);
    } catch {
      return; // Stay in edit mode; the caller surfaces the error.
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setDraft(value);
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="space-y-1.5">
        <div className="flex items-center gap-1.5">
          <Input
            id={inputId}
            aria-label={labels.input}
            className="h-8 text-sm"
            maxLength={255}
            placeholder={placeholder}
            value={draft}
            autoFocus
            disabled={disabled}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void handleSave();
              } else if (event.key === "Escape") {
                event.preventDefault();
                handleCancel();
              }
            }}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={labels.save}
            disabled={saveBlocked}
            onClick={() => void handleSave()}
          >
            <Check className="size-4" />
          </Button>
          <Button type="button" variant="ghost" size="icon-sm" aria-label={labels.cancel} onClick={handleCancel}>
            <X className="size-4" />
          </Button>
        </div>
        {help ? <p className="text-xs text-muted-foreground">{help}</p> : null}
      </div>
    );
  }

  return (
    <div className="flex min-w-0 items-center gap-1.5">
      <h2 className="min-w-0 truncate text-base font-semibold">{children}</h2>
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        aria-label={labels.edit}
        title={help}
        disabled={disabled}
        onClick={() => {
          setDraft(value);
          setIsEditing(true);
        }}
      >
        <Pencil className="size-3.5" />
      </Button>
      {accessory}
    </div>
  );
}
