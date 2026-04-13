"use client";

import { useEffect, useRef } from "react";
import type { StreamEvent } from "@/types/events";

interface EventLogProps {
  events: StreamEvent[];
}

const typeColors: Record<string, string> = {
  connected: "text-green-400",
  func_pending: "text-yellow-400",
  lint_feedback: "text-cyan-400",
  analysis_start: "text-blue-400",
  architecture_detected: "text-purple-400",
  epoch_prediction: "text-amber-400",
  training_summary: "text-green-400",
  heartbeat: "text-gray-500",
  error: "text-red-400",
};

export default function EventLog({ events }: EventLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div
      ref={scrollRef}
      className="h-full overflow-y-auto font-mono text-xs space-y-0.5 p-2"
    >
      {events.length === 0 && (
        <span className="text-gray-500 italic">No events yet...</span>
      )}
      {events.map((evt, i) => (
        <div key={i} className="flex gap-2 leading-relaxed">
          <span className="text-gray-600 shrink-0">
            {new Date(evt.timestamp * 1000).toLocaleTimeString()}
          </span>
          <span className={`shrink-0 ${typeColors[evt.event_type] || "text-gray-400"}`}>
            [{evt.event_type}]
          </span>
          <span className="text-gray-300 break-all">{evt.message}</span>
        </div>
      ))}
    </div>
  );
}
