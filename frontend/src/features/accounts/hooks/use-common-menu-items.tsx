import { Copy, ScrollText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import type { DetailMenuItem } from "@/features/accounts/components/provider-detail";

/** Menu items every account page offers: copy its ID and open its request logs. */
export function useCommonMenuItems(id: string, logsAccountId: string): DetailMenuItem[] {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return [
    {
      key: "copy-id",
      label: t("providers.detail.copyId"),
      icon: <Copy />,
      onSelect: () => void navigator.clipboard.writeText(id),
    },
    {
      key: "logs",
      label: t("providers.detail.openLogs"),
      icon: <ScrollText />,
      onSelect: () => navigate("/logs?accountId=" + encodeURIComponent(logsAccountId)),
    },
  ];
}
