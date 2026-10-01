/** Readable labels for historical models no longer present in the catalog. */
export function modelDisplayName(id: string, catalogName?: string): string {
  const slug = id.trim().split("/").at(-1) ?? "";
  if (catalogName && catalogName !== id && catalogName !== slug) return catalogName;
  if (!slug) return "--";
  const [name, variant] = slug.split(":");
  const readable = name
    .replace(/-\d{8}$/, "")
    .replace(/(\d)-(\d)(?=-|$)/g, "$1.$2")
    .split(/[-_]/)
    .map((word) => /^(gpt|glm|ai|api)$/i.test(word)
      ? word.toUpperCase()
      : word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
  return variant ? `${readable} (${variant.charAt(0).toUpperCase() + variant.slice(1)})` : readable;
}
