# Medication Reconciliation & Conflict Reporting Service

## SWE Internship — Take Home Assignment Submission

This project implements a backend service that ingests medication lists from different sources, maintains patient medication history, and detects conflicts such as dose mismatches, unsafe drug combinations, and missing or stopped medications.

The goal of this assignment was to demonstrate clear system design, readable code, and well-reasoned tradeoffs within a limited time window rather than building a production-scale system.

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

- **app/main.py**  
  API endpoints and request handling.

- **app/conflDetect.py**  
  Core business logic for conflict detection.

- **app/db.py**  
  SQLite database operations.

- **app/models.py**  
  Data structure helpers.

- **data/conflict_rules.json**  
  Static rules for drug conflicts.

- **tests/**  
  Unit tests for conflict detection.

The goal was to keep the architecture simple and easy to understand.

---

## Design Decisions

### SQLite instead of MongoDB
SQLite was chosen because:

- No external setup required
- Easy for reviewers to run locally
- Sufficient for assignment scale
- Faster to implement within limited time

The focus was simplicity and reproducibility rather than scalability.

---

### Simple Rule Engine
Conflict rules are stored in a JSON file to keep behavior deterministic and easy to review.  
A production system would use standard medical databases like RxNorm.

---

### Simple Data Models
Plain Python dictionaries were used instead of complex modeling frameworks to reduce boilerplate and focus on core logic.

---

### Snapshot-based Storage
Each ingestion creates a new snapshot instead of modifying existing data.  
This preserves history and simplifies reconciliation.

---

### Synchronous Conflict Detection
Conflicts are detected during ingestion to keep the architecture straightforward.

---

## Assumptions

- Each patient belongs to a single clinic.
- Medication names are compared using simple normalization.
- Snapshots are append-only.
- Dataset size is small.
- No concurrent write handling.

---

## Tradeoffs

- SQLite is simple but not highly scalable.
- Static rules are limited in coverage.
- No medical terminology mapping.
- Data is stored in a denormalized format for simplicity.

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

## AI Usage Disclosure

AI tools were used as development assistance.

### Used AI for
- Adding comments and improving readability
- Drafting documentation
- Brainstorming design ideas

### Reviewed manually
- Core business logic
- Database design
- System architecture
- Tests

### Example of disagreement
AI suggested using MongoDB initially. I chose SQLite instead because it required less setup, was easier for reviewers to run, and was sufficient for this assignment.

---

## Final Notes

The focus of this submission was to demonstrate clear thinking, practical system design, and maintainable code within a limited time window.
