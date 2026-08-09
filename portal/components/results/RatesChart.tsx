"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";

export interface RateBar {
  label: string;
  value: number;
  color: "accept" | "reject" | "accent";
}

const COLOR_VAR: Record<RateBar["color"], string> = {
  accept: "var(--accept)",
  reject: "var(--reject)",
  accent: "var(--accent-c)",
};

/**
 * Small client-island bar chart for rates (APCER/BPCER, red-team success
 * rate by check family) — a fixed-height ResponsiveContainer, one bar per
 * category. Deliberately not used for the confusion matrix (a species x
 * check grid doesn't chart well as bars; that's a table in page.tsx).
 */
export function RatesChart({ data, unit = "%" }: { data: RateBar[]; unit?: string }) {
  const chartData = data.map((d) => ({ ...d, displayValue: Math.round(d.value * 1000) / 10 }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(120, data.length * 48)}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 32, bottom: 4, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-c)" horizontal={false} />
        <XAxis
          type="number"
          domain={[0, 100]}
          tick={{ fill: "var(--text-2)", fontSize: 11 }}
          tickFormatter={(v) => `${v}${unit}`}
          stroke="var(--border-c)"
        />
        <YAxis
          type="category"
          dataKey="label"
          width={160}
          tick={{ fill: "var(--text-2)", fontSize: 11 }}
          stroke="var(--border-c)"
        />
        <Bar dataKey="displayValue" radius={[0, 4, 4, 0]} barSize={20}>
          {chartData.map((entry) => (
            <Cell key={entry.label} fill={COLOR_VAR[entry.color]} />
          ))}
          <LabelList
            dataKey="displayValue"
            position="right"
            formatter={(v) => `${v ?? 0}${unit}`}
            style={{ fill: "var(--text-2)", fontSize: 11, fontFamily: "var(--font-mono)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
