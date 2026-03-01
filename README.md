# Medication Reconciliation & Conflict Reporting Service

## SWE Internship — Take Home Assignment Submission

This project implements a backend service that ingests medication lists from different sources, maintains patient medication history, and detects conflicts such as dose mismatches, unsafe drug combinations, and missing or stopped medications.

The goal of this assignment was to demonstrate clear system design, readable code, and well-reasoned tradeoffs within a limited time window rather than building a production-scale system.

---

## Assumptions

Before starting implementation, I made the following assumptions to keep scope manageable:

- Each patient belongs to a single clinic.
- Medication names are compared using simple normalization (lowercase string matching).
- Snapshots are append-only and not modified after creation.
- Dataset size is small.
- No concurrent write handling is required.
- Conflict detection runs during ingestion rather than asynchronously.

These assumptions helped reduce complexity and allowed focus on core reconciliation logic.

---

## Design Choices and AI Usage

AI tools were used for assistance (comments, documentation drafting, and brainstorming ideas), but all design decisions were reviewed manually. In several cases I chose simpler alternatives than what AI initially suggested.

### SQLite instead of MongoDB (AI suggested MongoDB)
I chose SQLite because:

- No external setup required
- Easier for reviewers to run locally
- Sufficient for assignment scale
- Faster implementation in a time-boxed task
- Keeps the project self-contained

This prioritizes reproducibility over scalability.

---

### Static JSON Rule Engine
AI suggested more complex or dynamic approaches, but I chose static JSON rules because:

- Deterministic behavior
- Easy to review
- No external dependencies
- Faster implementation

A production system would integrate medical databases like RxNorm.

---

### Simple Python Data Models
Instead of heavier modeling frameworks, I used simple dictionary-based models because:

- Less boilerplate
- Faster development
- Easier testing
- Keeps focus on business logic

---

### Snapshot-Based Storage
Each ingestion creates a new snapshot rather than modifying previous data.  
This preserves history and simplifies reconciliation logic.

---

### Synchronous Conflict Detection
Conflicts are detected immediately during ingestion to keep the system straightforward.  
AI suggested more complex background processing, but synchronous detection was sufficient for this assignment.

---

## Quick Setup

### Requirements
- Python 3.9+
- Git

### Steps

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
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:

```
http://localhost:8000/docs
```

to view API documentation.

---

## Problem Overview

Dialysis patients may receive medication prescriptions from multiple sources such as clinic records, hospital discharge notes, or patient self reports. This can lead to inconsistencies like:

- Same medication with different doses
- Unsafe drug combinations
- Medication missing or stopped in one source

This service stores medication snapshots, detects conflicts, and tracks unresolved issues.

---

## Architecture Overview

The system follows a simple flow:

```
Client Request → FastAPI → Conflict Detection → SQLite Database → Response
```

### Main Components

- **app/main.py** — API endpoints and request handling  
- **app/conflDetect.py** — conflict detection logic  
- **app/db.py** — SQLite database operations  
- **app/models.py** — data structure helpers  
- **data/conflict_rules.json** — static conflict rules  
- **tests/** — unit tests for core logic  

The architecture is intentionally simple and easy to follow.

---

## Tradeoffs

- SQLite is simple but not highly scalable.
- Static rules provide limited medical coverage.
- No drug alias or terminology mapping.
- Denormalized storage simplifies implementation but increases record size.

---

## Tests

Tests focus on core business logic:

- Dose mismatch detection
- Blacklisted drug combinations
- Missing or stopped medications
- Edge cases

Run tests using:

```bash
pytest tests/ -v
```

---

## API Endpoints

- **POST /ingest** — ingest medication snapshot and detect conflicts  
- **GET /patients/{patId}** — fetch patient summary  
- **POST /conflicts/{patId}/{confIdx}/resolve** — resolve a conflict  
- **GET /health** — service health check

---

## Known Limitations

- No drug alias mapping or medical terminology integration.
- Basic validation only.
- No authentication or authorization.
- No audit event log.
- SQLite not suitable for large production workloads.

---

## Future Improvements

With more time, I would add:

- Drug name standardization using medical databases
- Strong request validation
- Scalable database support
- Background conflict detection
- Audit logging
- UI dashboard

---

## Extension Request

Due to technical issues with my laptop today, I request permission to submit the demo video link by **tomorrow 12:00 noon**.  
The implementation is complete and working — only the recording is pending.

---

