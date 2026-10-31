import { ChevronDown, LogIn, RefreshCw, Upload } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/** Re-authenticate action of subscription accounts that can either sign in again or import a credential file. */
export function ReauthenticateMenu({
  disabled,
  onSignIn,
  onImport,
}: {
  disabled: boolean;
  onSignIn: () => void;
  onImport: () => void;
}) {
  const { t } = useTranslation();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" size="sm" variant="outline" className="h-8 gap-1.5 text-xs" disabled={disabled}>
          <RefreshCw className="h-3.5 w-3.5" />
          {t("common.actions.reauthenticate")}
          <ChevronDown className="h-3 w-3 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuItem onSelect={onSignIn}>
          <LogIn className="h-3.5 w-3.5" />
          {t("accounts.reauthMenu.signIn")}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={onImport}>
          <Upload className="h-3.5 w-3.5" />
          {t("accounts.reauthMenu.import")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
