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

  const runFunction = (name) => {
  setOutput('');
  const eventSource = new EventSource(`${API_BASE}/stream/${name}`);

  eventSource.onmessage = (e) => {
    setOutput(prev => prev + '\n' + e.data);
  };

  eventSource.onerror = (err) => {
    setOutput(prev => prev + '\n❌ Error pada koneksi streaming.');
    eventSource.close();
  };
};
 

  return (
    <div style={{
      fontFamily: 'Segoe UI, sans-serif',
      padding: '2rem',
      maxWidth: '700px',
      margin: '0 auto',
    }}>
      <h1 style={{ textAlign: 'center', marginBottom: '1rem' }}>📊 Automasi Google Sheet</h1>
      <h2 style={{ marginBottom: '1rem' }}>🛠 Pilih Fungsi:</h2>

      {functions.length === 0 ? (
        <p>🔄 Memuat fungsi...</p>
      ) : (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
        }}>
          {functions.map(fn => (
            <button
              key={fn}
              onClick={() => runFunction(fn)}
              disabled={loading}
              style={{
                backgroundColor: loading ? '#999' : '#4CAF50',
                color: 'white',
                padding: '0.75rem 1rem',
                border: 'none',
                borderRadius: '5px',
                fontSize: '1rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.3s ease'
              }}
            >
              {fn.replace('main_', '').replace(/_/g, ' ').toUpperCase()}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <p style={{ marginTop: '1rem', color: '#666' }}>⏳ Sedang diproses...</p>
      )}

      <h3 style={{ marginTop: '2rem' }}>📋 Output:</h3>
      <pre style={{
        backgroundColor: '#f4f4f4',
        color: '#333',
        padding: '1rem',
        borderRadius: '8px',
        maxHeight: '400px',
        overflowY: 'auto',
        whiteSpace: 'pre-wrap',
        lineHeight: '1.5',
        fontFamily: 'Consolas, monospace'
      }}>
        {output}
      </pre>
    </div>
  );
}
