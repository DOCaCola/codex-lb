import { Pause, Play } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

export function AccountPauseButton({
  paused,
  disabled,
  onClick,
}: {
  paused: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const { t } = useTranslation();
  const Icon = paused ? Play : Pause;
  return (
    <Button
      type="button"
      size="sm"
      variant={paused ? "default" : "outline"}
      className="h-8 gap-1.5 text-xs"
      disabled={disabled}
      onClick={onClick}
    >
      <Icon className="h-3.5 w-3.5" />
      {t(paused ? "common.actions.resume" : "common.actions.pause")}
    </Button>
  );
}
