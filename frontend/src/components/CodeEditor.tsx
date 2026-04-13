"use client";

import dynamic from "next/dynamic";
import { useCallback, useRef } from "react";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-gray-900 text-gray-400">
      Loading editor...
    </div>
  ),
});

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export default function CodeEditor({ value, onChange, onSubmit }: CodeEditorProps) {
  const editorRef = useRef<unknown>(null);

  const handleMount = useCallback((editor: unknown) => {
    editorRef.current = editor;
  }, []);

  const handleChange = useCallback(
    (val: string | undefined) => {
      onChange(val ?? "");
    },
    [onChange]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-sm text-gray-300 font-mono">pytorch_code.py</span>
        <button
          onClick={onSubmit}
          className="px-4 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors"
        >
          Submit (Return)
        </button>
      </div>
      <div className="flex-1">
        <MonacoEditor
          height="100%"
          language="python"
          theme="vs-dark"
          value={value}
          onChange={handleChange}
          onMount={handleMount}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: "on",
          }}
        />
      </div>
    </div>
  );
}
