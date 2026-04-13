/** Shared types matching the FastAPI backend event models. */

export type EventType =
  | "connected"
  | "error"
  | "heartbeat"
  | "func_pending"
  | "lint_feedback"
  | "analysis_start"
  | "architecture_detected"
  | "epoch_prediction"
  | "training_summary";

export type ClientAction = "update" | "return" | "cancel";

export interface ClientMessage {
  action: ClientAction;
  code?: string;
  stream_interval?: number;
}

export interface LintIssue {
  line: number;
  column: number;
  severity: string;
  message: string;
}

export interface PendingFunction {
  name: string;
  line: number;
  signature: string;
  status: "pending" | "analyzing" | "done";
}

export interface ArchitectureInfo {
  model_type: string;
  layers: string[];
  optimizer: string;
  loss_function: string;
  dataset: string;
  batch_size: number | null;
  learning_rate: number | null;
  total_epochs: number | null;
  device: string;
}

export interface EpochMetrics {
  epoch: number;
  total_epochs: number;
  train_loss: number;
  val_loss: number | null;
  train_accuracy: number | null;
  val_accuracy: number | null;
  learning_rate: number | null;
  elapsed_time_estimate: string;
  eta: string;
}

export interface TrainingSummary {
  total_epochs: number;
  final_train_loss: number;
  final_val_loss: number | null;
  final_train_accuracy: number | null;
  final_val_accuracy: number | null;
  best_epoch: number | null;
  convergence_analysis: string;
  recommendations: string[];
}

export interface StreamEvent {
  event_type: EventType;
  data: Record<string, unknown>;
  message: string;
  timestamp: number;
}
