import { FileJson, Upload } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function formatSize(bytes: number): string {
  return bytes < 1024 ? `${bytes} B` : `${Math.ceil(bytes / 1024)} KB`;
}

export type CredentialFileAreaProps = {
  files: File[];
  multiple?: boolean;
  disabled?: boolean;
  /** Accessible name of the file input. */
  label: string;
  onChange: (files: File[]) => void;
};

/** Drop zone and file list shared by every credential import dialog. */
export function CredentialFileArea({ files, multiple = false, disabled = false, label, onChange }: CredentialFileAreaProps) {
  const { t } = useTranslation();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const accept = (list: FileList | null) => {
    const chosen = Array.from(list ?? []);
    if (chosen.length > 0) onChange(multiple ? chosen : chosen.slice(0, 1));
  };
  const drop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    if (!disabled) accept(event.dataTransfer.files);
  };
  const input = (
    <input
      ref={inputRef}
      id={inputId}
      type="file"
      accept="application/json,.json"
      multiple={multiple}
      disabled={disabled}
      aria-label={label}
      className="sr-only"
      onChange={(event) => {
        accept(event.currentTarget.files);
        event.currentTarget.value = "";
      }}
    />
  );

  if (files.length > 0 && !multiple) {
    const [file] = files;
    return (
      <div className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs">
        {input}
        <FileJson className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate font-mono" title={file.name}>{file.name}</span>
        <span className="text-muted-foreground">{formatSize(file.size)}</span>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-7 px-2 text-xs"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          {t("accounts.fileArea.change")}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label
        htmlFor={inputId}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border border-dashed p-5 text-center text-xs text-muted-foreground transition-colors hover:bg-muted/40",
          dragging && "border-primary bg-primary/5",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        {input}
        <Upload className="h-4 w-4" aria-hidden="true" />
        <span>
          {multiple ? t("accounts.fileArea.dropMany") : t("accounts.fileArea.dropOne")}{" "}
          <span className="underline">{multiple ? t("accounts.fileArea.chooseMany") : t("accounts.fileArea.chooseOne")}</span>
        </span>
      </label>
      {files.length > 0 ? (
        <ul className="max-h-32 space-y-1.5 overflow-y-auto" aria-label={t("accounts.importDialog.selectedFiles")}>
          {files.map((file, index) => (
            <li
              key={`${file.name}-${file.size}-${file.lastModified}-${index}`}
              className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs"
            >
              <FileJson className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate font-mono" title={file.name}>{file.name}</span>
              <span className="text-muted-foreground">{formatSize(file.size)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
