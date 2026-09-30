# Architecture Documentation

## System Overview
The **SIH 2026 Acoustic Livestock Health Early-Warning System** is an offline-first, AI-driven monitoring platform that analyzes shed acoustic signals (coughing, distress vocalizations, rumination anomalies) to detect early indicators of livestock respiratory illness.

> **Medical Disclaimer**: This system generates statistical anomaly alerts requiring veterinary verification. It does NOT provide automated medical diagnoses or treatment prescriptions.

## High-Level Architecture

```
[Shed Microphones] ──> [Edge AI Device (TFLite YAMNet Classifier)]
                               │
                       (Store & Forward)
                               │
                       [FastAPI Gateway]
                               ├──> [PostgreSQL Database]
                               ├──> [Python ML Microservice (Re-Validation)]
                               ├──> [SLA Escalation Engine]
                               ├──> [Tamper-Evident Ledger (Audit Hash Chain)]
                               └──> [React + TypeScript Dashboard]
```

## Key Subsystems
1. **Edge AI & Offline Sync**: Audio preprocessor running YAMNet embeddings + lightweight TFLite classifier on edge devices, caching offline via SQLite.
2. **FastAPI Core Backend**: Handles acoustic event ingestion, alert lifecycle management, SLA escalation state machine, and veterinary referral workflows.
3. **Python ML Service**: High-fidelity feature extraction & cloud model re-validation endpoint.
4. **Audit Hash Chain**: Immutable sha256 block hash ledger ensuring non-repudiation of alert histories and clinical verification actions.
5. **Geospatial Frontend**: React + TypeScript + Vite web app with Leaflet outbreak mapping and SLA workbench.
