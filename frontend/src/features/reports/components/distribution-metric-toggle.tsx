import { ChartToggle } from "@/components/chart-toggle";

export type DistributionMetric = "cost" | "req";

type DistributionMetricToggleProps = {
  metric: DistributionMetric;
  onChange: (metric: DistributionMetric) => void;
};

const OPTIONS: DistributionMetric[] = ["cost", "req"];

export function DistributionMetricToggle({ metric, onChange }: DistributionMetricToggleProps) {
  return (
    <ChartToggle
      label="Distribution metric"
      value={metric}
      options={OPTIONS.map((option) => ({ value: option, label: option }))}
      onChange={onChange}
    />
  );
}
