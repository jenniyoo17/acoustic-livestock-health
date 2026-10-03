# SIH Demo Guide

This document describes the shortest practical end-to-end demo flow for the current repository state.

## 1. Start the services

Backend:

```sh
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

ML service:

```sh
cd ml_service
python -m uvicorn src.main:app --reload --port 8001
```

Edge simulator:

```sh
cd edge_simulator
python -m uvicorn src.main:app --reload --port 8002
```

Frontend:

```sh
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

## 2. Open the Command Center

Visit the frontend dashboard in the browser. Confirm the default landing page loads and the medical disclaimer is visible.

## 3. Generate an acoustic event using the edge simulator

```sh
cd edge_simulator
python cli.py generate --count 3 --event-type Cough --confidence 0.91
python cli.py queue
```

This creates local queued events and shows the queue state. The queue is stored in the simulator-local SQLite database and remains UNSYNCED until the backend accepts a batch.

## 4. Demonstrate offline queue behavior

Use the edge CLI to inspect the queue and confirm that generated events are queued locally before sync:

```sh
cd edge_simulator
python cli.py status
python cli.py queue
```

This is the offline-first workflow. Network issues or backend unavailability leave the queue in UNSYNCED state.

## 5. Sync the event

```sh
cd edge_simulator
python cli.py sync
```

The sync action attempts the existing backend contract using the queue's batch logic, max batch size of 50, idempotent handling, and SHA-256 batch verification.

## 6. Show alert creation and SLA state

Open the dashboard and select the Alerts & SLA page. Confirm that the alert appears in the operations board and that the SLA tier and deadline are visible.

## 7. Acknowledge the alert

From the dashboard or backend API, acknowledge the active alert on the current SLA tier. The workflow is intentionally demo-only and should remain within the operational rules.

## 8. Perform vet verification

Open the Vet / Lab Workbench and choose the alert under review. Submit a human verification outcome such as Verified_Risk or False_Positive.

## 9. Create a lab referral

Create a lab referral for a Verified_Risk result and then change the referral status through the workflow states.

Example status progression:

```sh
Pending -> Sample_Collected -> In_Lab -> Result_Available
```

## 10. Open the Audit Ledger

Open the Audit Ledger page and click Verify Integrity. The UI should show the tamper-evident ledger and the verification result.

## 11. Verify final backend state

Use the backend and edge CLI outputs to confirm that the event has moved from queue to backend ingestion through alert, SLA, vet, and lab flow. The ledger should also illustrate the audit trail for those actions.

## 12. Government export view

Open the Government Export page. The frontend should show the current backend result or the real unavailable state if the export endpoint is not exposed in the active backend build.

## Demo Notes

- The project remains a demonstration system, not a clinical or production deployment.
- The classifier remains UNTRAINED_DEMO and must not be described as clinically validated.
- The audit ledger is a tamper-evident SHA-256 chain and is not a blockchain.
- The medical boundary remains: "Acoustic Early-Warning & Anomaly Detection only."
