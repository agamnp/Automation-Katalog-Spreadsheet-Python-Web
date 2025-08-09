"use client";

import React, { useState, useEffect } from "react";

export default function AutomasiSheet() {
  const [functions, setFunctions] = useState([]);
  const [selectedFunc, setSelectedFunc] = useState("");
  const [logs, setLogs] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [eventSource, setEventSource] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/functions")
      .then((res) => res.json())
      .then((data) => {
        setFunctions(data.functions || []);
        if (data.functions?.length) {
          setSelectedFunc(data.functions[0]);
        }
      });
  }, []);

  const startStreaming = () => {
    if (!selectedFunc) return;
    const source = new EventSource(`http://localhost:8000/stream/${selectedFunc}`);
    setEventSource(source);
    setIsStreaming(true);
    setLogs(["Loading..."]);

    source.onmessage = (e) => {
      if (e.data === "✅ Proses selesai") {
        setIsStreaming(false);
        source.close();
      }
      setLogs((prev) => [...prev, e.data]);
    };

    source.onerror = () => {
      setIsStreaming(false);
      setLogs((prev) => [...prev, "❌ Koneksi terputus."]);
      source.close();
    };
  };

  const stopStreaming = () => {
    if (eventSource) {
      eventSource.close();
      setIsStreaming(false);
      setLogs((prev) => [...prev, "⛔ Dihentikan manual oleh pengguna."]);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <div className="bg-white text-black rounded-lg shadow-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-6 flex items-center justify-center gap-2">
          <span role="img" aria-label="icon">📊</span>
          Automasi Google Sheet
        </h1>

        <label className="block font-semibold mb-1 text-gray-700">
          🛠️ Pilih Fungsi:
        </label>
        <select
          value={selectedFunc}
          onChange={(e) => setSelectedFunc(e.target.value)}
          className="w-full border px-3 py-2 rounded mb-4"
        >
          {functions.map((fn) => (
            <option key={fn} value={fn}>
              {fn}
            </option>
          ))}
        </select>

        <button
          onClick={startStreaming}
          disabled={isStreaming}
          className={`w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition duration-200 ${isStreaming && "opacity-50 cursor-not-allowed"}`}
        >
          Jalankan
        </button>

        {isStreaming && (
          <button
            onClick={stopStreaming}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded mt-2 transition duration-200"
          >
            ⛔ Stop
          </button>
        )}

        <div className="mt-6">
          <label className="block font-semibold mb-1 text-gray-700">
            🧾 Output:
          </label>
          <textarea
            value={logs.join("\n")}
            readOnly
            rows={10}
            className="w-full border px-3 py-2 rounded resize-none font-mono text-xs bg-gray-50"
          />
        </div>
      </div>
    </div>
  );
}
