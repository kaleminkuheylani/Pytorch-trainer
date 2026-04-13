"use client";

import type { PendingFunction, LintIssue } from "@/types/events";

interface PendingPanelProps {
  functions: PendingFunction[];
  lintIssues: LintIssue[];
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  analyzing: "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse",
  done: "bg-green-500/20 text-green-400 border-green-500/30",
};

const severityColors: Record<string, string> = {
  info: "text-blue-400",
  warning: "text-yellow-400",
  error: "text-red-400",
};

export default function PendingPanel({ functions, lintIssues }: PendingPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Pending Functions */}
      {functions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-300 mb-2">
            Functions
          </h3>
          <div className="space-y-1">
            {functions.map((fn) => (
              <div
                key={fn.name}
                className={`flex items-center gap-2 px-3 py-1.5 rounded border text-sm font-mono ${statusColors[fn.status] || statusColors.pending}`}
              >
                <span className="text-xs uppercase tracking-wider opacity-70">
                  {fn.status}
                </span>
                <span>{fn.signature}</span>
                <span className="text-xs opacity-50 ml-auto">L{fn.line}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lint Issues */}
      {lintIssues.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-300 mb-2">
            Lint ({lintIssues.length})
          </h3>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {lintIssues.map((issue, i) => (
              <div
                key={`${issue.line}-${i}`}
                className="flex items-start gap-2 text-xs font-mono"
              >
                {issue.line > 0 && (
                  <span className="text-gray-500 shrink-0">L{issue.line}</span>
                )}
                <span className={severityColors[issue.severity] || "text-gray-400"}>
                  [{issue.severity}]
                </span>
                <span className="text-gray-300">{issue.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {functions.length === 0 && lintIssues.length === 0 && (
        <p className="text-sm text-gray-500 italic">
          Start typing PyTorch code. Functions will appear here as pending.
        </p>
      )}
    </div>
  );
}
