"use client";

import { useCallback, useRef, useState } from "react";
import CodeEditor from "@/components/CodeEditor";
import PendingPanel from "@/components/PendingPanel";
import MetricsDashboard from "@/components/MetricsDashboard";
import EventLog from "@/components/EventLog";
import { useAgentSocket } from "@/hooks/useAgentSocket";

const SAMPLE_CODE = `import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# --- Model ---
class SimpleCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.pool = nn.MaxPool2d(2)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.25)

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.dropout(x)
        x = torch.flatten(x, 1)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

# --- Training ---
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    train_dataset = datasets.MNIST('./data', train=True, download=True, transform=transform)
    test_dataset = datasets.MNIST('./data', train=False, transform=transform)

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=1000)

    model = SimpleCNN().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(1, 11):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = output.max(1)
            total += target.size(0)
            correct += predicted.eq(target).sum().item()

        train_loss = running_loss / len(train_loader)
        train_acc = 100. * correct / total
        print(f"Epoch {epoch}: loss={train_loss:.4f}, acc={train_acc:.1f}%")

if __name__ == "__main__":
    train()
`;

export default function Home() {
  const [code, setCode] = useState(SAMPLE_CODE);
  const { state, sendUpdate, sendReturn, sendCancel, resetState } = useAgentSocket();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCodeChange = useCallback(
    (newCode: string) => {
      setCode(newCode);
      // Debounce updates to server
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        sendUpdate(newCode);
      }, 500);
    },
    [sendUpdate]
  );

  const handleSubmit = useCallback(() => {
    sendReturn(code);
  }, [code, sendReturn]);

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold tracking-tight">PyTorch Agent Stream</h1>
          <span
            className={`w-2 h-2 rounded-full ${
              state.connected ? "bg-green-400" : "bg-red-400"
            }`}
            title={state.connected ? "Connected" : "Disconnected"}
          />
        </div>
        <div className="flex items-center gap-2">
          {state.analyzing && (
            <button
              onClick={sendCancel}
              className="px-3 py-1 text-sm bg-red-600/20 text-red-400 border border-red-600/30 rounded hover:bg-red-600/30 transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            onClick={resetState}
            className="px-3 py-1 text-sm bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition-colors"
          >
            Clear
          </button>
        </div>
      </header>

      {/* Error banner */}
      {state.error && (
        <div className="px-6 py-2 bg-red-900/30 border-b border-red-800 text-sm text-red-300">
          {state.error}
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Code Editor */}
        <div className="flex flex-col w-1/2 border-r border-gray-800">
          <div className="flex-1">
            <CodeEditor
              value={code}
              onChange={handleCodeChange}
              onSubmit={handleSubmit}
            />
          </div>
          {/* Pending panel under editor */}
          <div className="h-48 border-t border-gray-800 p-3 overflow-y-auto bg-gray-900/50">
            <PendingPanel
              functions={state.pendingFunctions}
              lintIssues={state.lintIssues}
            />
          </div>
        </div>

        {/* Right: Metrics + Event Log */}
        <div className="flex flex-col w-1/2">
          <div className="flex-1 overflow-y-auto p-4">
            <MetricsDashboard
              architecture={state.architecture}
              epochs={state.epochs}
              summary={state.summary}
              analyzing={state.analyzing}
            />
          </div>
          <div className="h-48 border-t border-gray-800 bg-gray-900/50">
            <div className="flex items-center px-3 py-1.5 border-b border-gray-800">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Event Log ({state.events.length})
              </span>
            </div>
            <EventLog events={state.events} />
          </div>
        </div>
      </div>
    </div>
  );
}
