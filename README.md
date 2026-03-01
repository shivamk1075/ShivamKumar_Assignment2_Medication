# Medication Reconciliation & Conflict Reporting Service

## SWE Internship — Take Home Assignment Submission

This project implements a backend service that ingests medication lists from multiple sources, maintains patient medication history, and detects clinically relevant conflicts such as dose mismatches, blacklisted drug combinations, and missing/stopped medications.

The focus of this assignment was **clear system design, readable code, and well-reasoned tradeoffs** rather than building a production-scale system.

---

# ⏱ Expected Time Window

**Time spent:** ~6–10 hours (time-boxed as instructed)

If anything appears incomplete, it was intentionally scoped to stay within the assignment constraints.

---

# 🚀 Quick Setup (Run in under 5 minutes)

## Requirements
- Python 3.9+
- Git

## Steps

```bash
# Clone repository
git clone git@github.com:shivamk1075/ShivamKumar_Assignment2_Medication.git
cd ShivamKumar_Assignment2_Medication

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Visit:

```
http://localhost:8001/docs
```

for interactive API documentation.

---

# 🎯 Problem Overview

Dialysis patients often receive medications from multiple sources:

- Clinic EMR
- Hospital discharge notes
- Patient self reports

This creates inconsistencies like:

- Same drug with different doses
- Dangerous drug combinations
- Medications missing or stopped in one source

This service:

- Stores medication snapshots
- Detects conflicts automatically
- Tracks unresolved conflicts
- Allows conflict resolution

---

# 🏗 Architecture Overview

The system follows a simple request → processing → storage flow.

```
Client Request
      ↓
FastAPI Endpoint
      ↓
Conflict Detection Engine
      ↓
SQLite Database
      ↓
Response / Reports
```

## Components

### `app/main.py`
- FastAPI endpoints
- Request handling
- Validation and orchestration

### `app/conflDetect.py`
- Core business logic
- Detects:
  - Dose mismatch
  - Blacklisted drug combinations
  - Missing/stopped medication

### `app/db.py`
- SQLite persistence layer
- Stores patient snapshots and conflicts

### `app/models.py`
- Data structure helpers (dictionary factories)

### `data/conflict_rules.json`
- Static conflict rules and drug classes

### `tests/`
- Unit tests for core conflict detection logic

---

# 🧠 System Design Decisions (Why things were chosen)

## SQLite instead of MongoDB
Originally MongoDB was considered, but SQLite was chosen because:

- Zero external setup required
- Easy for reviewers to run locally
- Sufficient for assignment scale
- Faster development in a time-boxed task
- Keeps project self-contained

This was a deliberate tradeoff prioritizing simplicity over scalability.

---

## Simple Rule Engine using JSON
Conflict rules are stored in a static JSON file.

Reasons:

- Easy to review
- Deterministic behavior
- No dependency on external APIs
- Faster implementation for assignment scope

A production system would integrate medical standards like RxNorm.

---

## Plain Python Data Models (not heavy frameworks)
Simple dictionary factories were used instead of complex modeling libraries.

Reasons:

- Reduced boilerplate
- Faster development
- Easier to test core logic
- Keeps focus on business rules

---

## Snapshot Based Storage
Each ingestion creates a new snapshot rather than modifying previous data.

Reasons:

- Preserves history
- Simplifies reconciliation logic
- Easier debugging

---

## Synchronous Conflict Detection
Conflicts are detected immediately during ingestion.

Reason:
- Simpler architecture for assignment scope.

Production systems may use background jobs.

---

# 📌 Assumptions

- Single clinic per patient.
- Medication names normalized using simple string comparison.
- Snapshots are append-only.
- Small dataset (assignment scale).
- No concurrent write conflicts.

---

# ⚖ Tradeoffs

| Choice | Benefit | Limitation |
|---|---|---|
| SQLite | Simple, serverless | Not horizontally scalable |
| Static rules | Deterministic | Limited medical coverage |
| Denormalized storage | Easy implementation | Larger record size |
| No RxNorm mapping | Faster build | Drug alias issues |

---

# 🧪 Tests

Tests focus on **core domain behavior** rather than framework code.

## Covered cases

- Dose mismatch detection
- Blacklisted drug combinations
- Missing/stopped medication
- Edge cases (empty data, normalization)

Run:

```bash
pytest tests/ -v
```

---

# 📊 API Overview

## POST `/ingest`
Ingest medication snapshot and detect conflicts.

## GET `/patients/{patId}`
Fetch patient summary and unresolved conflicts.

## POST `/conflicts/{patId}/{confIdx}/resolve`
Resolve a conflict with reason and audit info.

## GET `/health`
Service health check.

---

# 📦 Seed Data

A synthetic dataset generator was planned for quick demo data.

If not present, tests still demonstrate core functionality.

---

# ❗ Known Limitations

- No medical terminology mapping (RxNorm).
- No authentication or authorization.
- No audit event log (mutates conflicts directly).
- Basic validation only.
- SQLite not suitable for large production workloads.
- Limited reporting endpoints.

---

# 🔮 What I Would Build Next (With More Time)

- RxNorm drug mapping
- Strong request validation models
- PostgreSQL or MongoDB backend
- Event sourcing / audit logs
- Background conflict detection
- Authentication and permissions
- UI dashboard
- Better reporting analytics

---

# 🤖 AI Usage Disclosure

AI was used as a development assistant, not as a replacement for reasoning.

## Used AI for
- Improving code comments
- README drafting and formatting
- Architecture brainstorming
- Minor debugging assistance

## Reviewed manually
- All business logic
- Database design
- Conflict detection rules
- Tests and system flow

## Example where I disagreed with AI
AI suggested using MongoDB initially.  
I chose SQLite instead because:

- Easier setup for reviewers
- No external infrastructure
- Sufficient for assignment scope
- Faster development

---

# ✅ How This Meets Evaluation Criteria

### Modeling
Clear domain entities: Patient, Snapshot, Conflict.

### Architecture
Separated API, business logic, and storage layers.

### Robustness
Handles missing values, normalization, and edge cases.

### Code Readability
Simple naming, minimal abstraction, focused logic.

### Communication
This README documents decisions and tradeoffs clearly.

---

# 👨‍💻 Final Notes

The goal of this submission was to demonstrate:

- Clear thinking
- Practical system design
- Tradeoff awareness
- Maintainable code

Rather than maximizing features, the focus was on building a small but complete, understandable system.
