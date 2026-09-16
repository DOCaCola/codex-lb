import { useState } from "react";
import type { Control } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { newRow, type ModelRow } from "./model-source-model-draft";
import type { ModelSourceFormValues } from "./model-source-form";
import { ModelSourceFormFields } from "./model-source-form-fields";

export function ModelSourceModelEditor({
  rows,
  onChange,
  control,
}: {
  rows: ModelRow[];
  onChange: (rows: ModelRow[]) => void;
  control: Control<ModelSourceFormValues>;
}) {
  const { t } = useTranslation();
  const [selectedKey, setSelectedKey] = useState(rows[0]?.key);
  const selected = rows.find((row) => row.key === selectedKey) ?? rows[0];
  const update = (patch: Partial<ModelRow>) => {
    onChange(
      rows.map((row) =>
        row.key === selected.key ? { ...row, ...patch } : row,
      ),
    );
  };
  return (
    <section className="space-y-4 border-t pt-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">{t("apiKeys.table.models")}</h3>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            const row = newRow();
            onChange([...rows, row]);
            setSelectedKey(row.key);
          }}
        >
          {t("modelSources.modelEditor.add")}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        {t("modelSources.modelEditor.description")}
      </p>
      {selected ? (
        <>
          <label className="block space-y-1 text-sm font-medium">
            <span>{t("modelSources.modelEditor.select")}</span>
            <select
              className="h-9 w-full rounded-md border bg-background px-3 text-sm"
              value={selected.key}
              onChange={(event) => setSelectedKey(event.target.value)}
            >
              {rows.map((row) => (
                <option key={row.key} value={row.key}>
                  {row.displayName ||
                    row.model ||
                    t("modelSources.modelEditor.newModel")}
                </option>
              ))}
            </select>
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm font-medium">
              <span>{t("modelSources.modelEditor.id")}</span>
              <Input
                value={selected.model}
                maxLength={255}
                onChange={(event) => update({ model: event.target.value })}
              />
            </label>
            <label className="space-y-1 text-sm font-medium">
              <span>{t("modelSources.modelEditor.displayName")}</span>
              <Input
                value={selected.displayName}
                maxLength={255}
                placeholder={selected.model}
                onChange={(event) =>
                  update({ displayName: event.target.value })
                }
              />
            </label>
          </div>
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={selected.isEnabled}
                onCheckedChange={(checked) =>
                  update({ isEnabled: checked === true })
                }
              />
              {t("modelSources.modelEditor.enabled")}
            </label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                onChange(rows.filter((row) => row.key !== selected.key))
              }
            >
              {t("modelSources.modelEditor.remove")}
            </Button>
          </div>
          <ModelSourceFormFields
            modelOnly
            control={control}
            draft={selected.draft}
            updateDraft={(patch) =>
              update({ draft: { ...selected.draft, ...patch } })
            }
            apiKeyLabel=""
          />
        </>
      ) : null}
    </section>
  );
}
