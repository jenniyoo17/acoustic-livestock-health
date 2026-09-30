import React from 'react';
import { Activity, ShieldAlert, Cpu, HeartPulse } from 'lucide-react';

export const App: React.FC = () => {
  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', color: '#f8fafc' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Activity size={32} color="#10b981" />
          <h1 style={{ margin: 0, fontSize: '1.875rem' }}>
            SIH 2026: Acoustic Livestock Health System
          </h1>
        </div>
        <p style={{ color: '#94a3b8', marginTop: '0.5rem', fontSize: '0.95rem' }}>
          Offline-First AI-Based Early-Warning Anomaly Detection System
        </p>
      </header>

      <main>
        <div
          style={{
            backgroundColor: '#1e293b',
            padding: '1rem 1.5rem',
            borderRadius: '0.5rem',
            borderLeft: '4px solid #f59e0b',
            marginBottom: '2rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontWeight: 600 }}>
            <ShieldAlert size={20} />
            <span>Important System Disclaimer</span>
          </div>
          <p style={{ color: '#cbd5e1', fontSize: '0.9rem', margin: '0.5rem 0 0 0' }}>
            This platform monitors acoustic signals for anomaly detection. It does <strong>NOT</strong> provide automated medical diagnoses or treatment prescriptions. All alerts require clinical verification by a registered veterinarian.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
          <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#38bdf8', marginBottom: '0.75rem' }}>
              <Cpu size={24} />
              <h3 style={{ margin: 0 }}>FastAPI Backend</h3>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: 0 }}>
              Async SQLAlchemy 2.0, PostgreSQL, Pydantic v2, and Ingestion APIs.
            </p>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#a78bfa', marginBottom: '0.75rem' }}>
              <HeartPulse size={24} />
              <h3 style={{ margin: 0 }}>Edge AI Simulator</h3>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: 0 }}>
              YAMNet feature extractor, TFLite classifier runtime, and offline store-and-forward engine.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
