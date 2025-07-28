// frontend/app/page.js
'use client';
import { useEffect, useState } from 'react';

export default function Page() {
  const [functions, setFunctions] = useState([]);
  const [output, setOutput] = useState('');
  const [loading, setLoading] = useState(false);

  const API_BASE = 'http://localhost:8000';

  useEffect(() => {
    fetch(`${API_BASE}/functions`)
      .then(res => res.json())
      .then(data => setFunctions(data.functions))
      .catch(err => setOutput('❌ Gagal ambil daftar fungsi'));
  }, []);

  const runFunction = async (name) => {
    setLoading(true);
    setOutput(`▶️ Menjalankan: ${name}...`);
    const res = await fetch(`${API_BASE}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    const data = await res.json();

    if (data.status === 'success') {
      setOutput(`✅ Output:\n\n${data.output.join('\n')}`);
    } else {
      setOutput(`❌ Error:\n\n${data.error}`);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h1>📊 Automasi Google Sheet</h1>
      <h2>🛠 Pilih Fungsi:</h2>

      {functions.length === 0 ? <p>Memuat fungsi...</p> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {functions.map(fn => (
            <button
              key={fn}
              onClick={() => runFunction(fn)}
              disabled={loading}
              style={{
                backgroundColor: '#2E8B57',
                color: 'White',
                padding: '10px',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer'
              }}
            >
              {fn.replace('main_', '').replace(/_/g, ' ').toUpperCase()}
            </button>
          ))}
        </div>
      )}

      <h3 style={{ marginTop: '2rem' }}>📋 Output:</h3>
      <pre style={{
        backgroundColor: '#eee',
        color: 'Black',
        padding: '1rem',
        borderRadius: '8px',
        maxHeight: '400px',
        overflowY: 'auto'
      }}>
        {output}
      </pre>
    </div>
  );
}
