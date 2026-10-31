import type { CSSProperties, ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

import "./plan-badge.css";

type ThemeColors = readonly [text: string, background: string, border: string];
type PlanColors = { light: ThemeColors; dark: ThemeColors };

const UNKNOWN_COLORS: PlanColors = {
  light: ["#52525b", "#f4f4f5", "#d4d4d8"],
  dark: ["#d4d4d8", "#27272a", "#52525b"],
};

const PLAN_COLORS = new Map<string, PlanColors>([
  ["free", {
    light: ["#475569", "#f1f5f9", "#cbd5e1"],
    dark: ["#cbd5e1", "#202b3b", "#46566c"],
  }],
  ["plus", {
    light: ["#047857", "#ecfdf5", "#a7f3d0"],
    dark: ["#6ee7b7", "#0a3025", "#1c6047"],
  }],
  ["prolite", {
    light: ["#a21caf", "#fdf4ff", "#f0abfc"],
    dark: ["#e879f9", "#35153e", "#72337d"],
  }],
  ["pro", {
    light: ["#6d28d9", "#f5f3ff", "#ddd6fe"],
    dark: ["#c4b5fd", "#281746", "#60438c"],
  }],
  ["team", {
    light: ["#0369a1", "#f0f9ff", "#bae6fd"],
    dark: ["#7dd3fc", "#0c2b40", "#285673"],
  }],
  ["business", {
    light: ["#0f766e", "#f0fdfa", "#99f6e4"],
    dark: ["#5eead4", "#0c3332", "#25615b"],
  }],
  ["enterprise", {
    light: ["#92400e", "#fffbeb", "#fde68a"],
    dark: ["#fcd34d", "#382c0b", "#756028"],
  }],
  ["edu", {
    light: ["#3f6212", "#f7fee7", "#d9f99d"],
    dark: ["#bef264", "#253311", "#526b2b"],
  }],
  ["max", {
    light: ["#be185d", "#fff1f2", "#fecdd3"],
    dark: ["#fda4af", "#3e1729", "#79334e"],
  }],
  ["ultra", {
    light: ["#1d4ed8", "#eff6ff", "#bfdbfe"],
    dark: ["#93b4ff", "#152951", "#35558d"],
  }],
  ["unknown", UNKNOWN_COLORS],
  ["guest", {
    light: ["#57534e", "#fafaf9", "#d6d3d1"],
    dark: ["#d6d3d1", "#292524", "#57534e"],
  }],
  ["go", {
    light: ["#0e7490", "#ecfeff", "#a5f3fc"],
    dark: ["#67e8f9", "#083344", "#155e75"],
  }],
  ["free_workspace", {
    light: ["#4338ca", "#eef2ff", "#c7d2fe"],
    dark: ["#a5b4fc", "#242454", "#4d4d99"],
  }],
  ["education", {
    light: ["#596418", "#f8fbe8", "#d3dc9f"],
    dark: ["#d5df8f", "#2d3118", "#626a34"],
  }],
  ["quorum", {
    light: ["#914b33", "#fff4ed", "#eec2ab"],
    dark: ["#e5ad92", "#39251b", "#78513d"],
  }],
  ["k12", {
    light: ["#b4333d", "#fff1f0", "#ffccd0"],
    dark: ["#ff8d94", "#411f24", "#85414a"],
  }],
]);

type PlanBadgeStyle = CSSProperties & Record<`--plan-${"light" | "dark"}-${"text" | "background" | "border"}`, string>;

export function PlanBadge({ plan, children }: { plan: string; children: ReactNode }) {
  const colors = PLAN_COLORS.get(plan) ?? UNKNOWN_COLORS;
  const style: PlanBadgeStyle = {
    "--plan-light-text": colors.light[0],
    "--plan-light-background": colors.light[1],
    "--plan-light-border": colors.light[2],
    "--plan-dark-text": colors.dark[0],
    "--plan-dark-background": colors.dark[1],
    "--plan-dark-border": colors.dark[2],
  };

  return (
    <Badge variant="outline" className="plan-badge" style={style}>
      {children}
    </Badge>
  );
}
