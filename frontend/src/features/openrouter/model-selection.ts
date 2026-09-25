import type { OpenRouterAccount } from "./api";

export type ModelSelectionKind = "models" | "images";
type CatalogModel = OpenRouterAccount["state"]["catalog"][number];

export function modelSelectionKind(
  model: CatalogModel | undefined,
): ModelSelectionKind {
  // Unavailable selections remain manageable in the general picker.
  return model?.image != null ? "images" : "models";
}
