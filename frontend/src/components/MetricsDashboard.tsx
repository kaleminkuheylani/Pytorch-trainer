"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { EpochMetrics, ArchitectureInfo, TrainingSummary } from "@/types/events";

interface MetricsDashboardProps {
  architecture: ArchitectureInfo | null;
  epochs: EpochMetrics[];
  summary: TrainingSummary | null;
  analyzing: boolean;
}

export default function MetricsDashboard({
  architecture,
  epochs,
  summary,
  analyzing,
}: MetricsDashboardProps) {
  const chartData = epochs.map((e) => ({
    epoch: e.epoch,
    "Train Loss": parseFloat(e.train_loss.toFixed(4)),
    "Val Loss": e.val_loss !== null ? parseFloat(e.val_loss.toFixed(4)) : undefined,
    "Train Acc": e.train_accuracy !== null ? parseFloat(e.train_accuracy.toFixed(1)) : undefined,
    "Val Acc": e.val_accuracy !== null ? parseFloat(e.val_accuracy.toFixed(1)) : undefined,
  }));

  const hasAccuracy = epochs.some((e) => e.train_accuracy !== null);

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto">
      {/* Architecture Info */}
      {architecture && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">Architecture</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <InfoRow label="Model" value={architecture.model_type} />
            <InfoRow label="Optimizer" value={architecture.optimizer} />
            <InfoRow label="Loss" value={architecture.loss_function} />
            <InfoRow label="Dataset" value={architecture.dataset} />
            <InfoRow label="Batch Size" value={architecture.batch_size?.toString() ?? "—"} />
            <InfoRow label="LR" value={architecture.learning_rate?.toString() ?? "—"} />
            <InfoRow label="Epochs" value={architecture.total_epochs?.toString() ?? "—"} />
            <InfoRow label="Device" value={architecture.device} />
          </div>
          {architecture.layers.length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-gray-500">Layers:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {architecture.layers.map((l, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300"
                  >
                    {l}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Loss Chart */}
      {chartData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">
            Loss
            {analyzing && (
              <span className="ml-2 text-xs text-blue-400 animate-pulse">streaming...</span>
            )}
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="epoch" stroke="#9CA3AF" fontSize={11} />
              <YAxis stroke="#9CA3AF" fontSize={11} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="Train Loss"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="Val Loss"
                stroke="#EF4444"
                strokeWidth={2}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Accuracy Chart */}
      {hasAccuracy && chartData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">Accuracy (%)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="epoch" stroke="#9CA3AF" fontSize={11} />
              <YAxis stroke="#9CA3AF" fontSize={11} domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="Train Acc"
                stroke="#10B981"
                strokeWidth={2}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="Val Acc"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Training Summary */}
      {summary && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-green-700/50">
          <h3 className="text-sm font-semibold text-green-400 mb-2">Training Summary</h3>
          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
            <InfoRow label="Final Train Loss" value={summary.final_train_loss.toFixed(4)} />
            <InfoRow
              label="Final Val Loss"
              value={summary.final_val_loss?.toFixed(4) ?? "—"}
            />
            <InfoRow
              label="Final Train Acc"
              value={
                summary.final_train_accuracy !== null
                  ? `${summary.final_train_accuracy.toFixed(1)}%`
                  : "—"
              }
            />
            <InfoRow
              label="Final Val Acc"
              value={
                summary.final_val_accuracy !== null
                  ? `${summary.final_val_accuracy.toFixed(1)}%`
                  : "—"
              }
            />
            <InfoRow label="Best Epoch" value={summary.best_epoch?.toString() ?? "—"} />
            <InfoRow label="Total Epochs" value={summary.total_epochs.toString()} />
          </div>
          {summary.convergence_analysis && (
            <p className="text-xs text-gray-300 mb-2">{summary.convergence_analysis}</p>
          )}
          {summary.recommendations.length > 0 && (
            <div>
              <span className="text-xs text-gray-500">Recommendations:</span>
              <ul className="list-disc list-inside mt-1 space-y-0.5">
                {summary.recommendations.map((rec, i) => (
                  <li key={i} className="text-xs text-gray-300">
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!architecture && epochs.length === 0 && !analyzing && (
        <div className="flex items-center justify-center h-32 text-gray-500 text-sm italic">
          Submit your code to see predicted training metrics here.
        </div>
      )}

      {/* Analyzing spinner */}
      {analyzing && epochs.length === 0 && (
        <div className="flex items-center justify-center h-32 gap-3">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-blue-400">Analyzing code...</span>
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-200 font-mono">{value}</span>
    </div>
  );
}
