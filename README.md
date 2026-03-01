# Medication Reconciliation & Conflict Reporting Service

A production-grade backend service for reconciling medications across multiple healthcare sources (clinic EMR, hospital discharge summaries, patient reports) and automatically detecting conflicts for dialysis patients.

## Features

✅ **Multi-source medication ingestion** — Accept medication lists from clinic EMR, hospital discharge, and patient self-reports  
✅ **Conflict detection** — Automatically flag dose mismatches, blacklisted drug combinations, and inconsistencies  
✅ **Longitudinal tracking** — Maintain version history of medication lists per patient  
✅ **Reporting & aggregation** — Query patients with unresolved conflicts, conflict statistics by clinic  
✅ **Conflict resolution workflow** — Mark conflicts resolved with audit trail (who, when, why)  

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  Ingestion       │         │  Retrieval       │              │
│  │  Endpoints       │────────▶│  Endpoints       │              │
│  │ POST /ingest     │         │ GET /patients    │              │
│  └──────────────────┘         │ POST /resolve    │              │
│          │                    └──────────────────┘              │
│          │                                                      │
│          ▼                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │  ConflictDetector                               │           │
│  │  ├─ detect_dose_mismatches()                    │           │
│  │  ├─ detect_blacklisted_combinations()           │           │
│  │  ├─ detect_missing_or_stopped()                 │           │
│  │  └─ detect_all_conflicts()                      │           │
│  └──────────────────────────────────────────────────┘           │
│          │                                                      │
│          ▼                                                      │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  Database        │         │  Reporting       │              │
│  │  Operations      │         │  Endpoints       │              │
│  │ └─ upsert        │         │ GET /conflicts   │              │
│  │ └─ get_patient   │────────▶│ GET /summary     │              │
│  │ └─ add_snapshot  │         └──────────────────┘              │
│  │ └─ add_conflicts │                                           │
│  └──────────────────┘                                           │
│          │                                                      │
│          ▼                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │  MongoDB (medication_reconciliation)            │           │
│  │  └─ patients (documents with snapshots + conflicts) │  │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Aspect | Decision | Trade-off |
|--------|----------|-----------|
| **Data Model** | Denormalized (snapshots + conflicts embedded in patient doc) | Single doc size grows over time; simpler joins. Future: archive old snapshots to separate collection |
| **Versioning** | Version via snapshot arrays (temporal sequence) | No explicit version numbers; ordering preserved by captured_at. Future: add version IDs for diff queries |
| **Conflict Resolution** | Mark in-place with metadata (reason, timestamp, user) | Mutation; could use event sourcing instead for full audit log |
| **Drug Database** | Static JSON rules (conflict_rules.json) | Extensible to SQL database (e.g., RxNorm). JSON keeps MVP simple |
| **Normalization** | Lowercase + trim at ingestion | Only stores normalized name in snapshots; original lost. Future: store both for reporting |

---

## Setup & Installation

### Prerequisites

- Python 3.9+
- MongoDB (local or Atlas)
- Git

### Quick Start (< 5 min)

```bash
# 1. Clone repository
git clone <your-repo>
cd medication-reconciliation

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set MongoDB connection
export MONGODB_URL="mongodb://localhost:27017"  # Default

# 5. Seed with synthetic data
python data/seed_data.py

# 6. Run tests
pytest tests/ -v

# 7. Start the server
uvicorn app.main:app --reload
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs (Swagger UI).

---

## API Endpoints

### Ingestion

**POST** `/api/v1/ingest`

Ingest medications from a source (clinic EMR, hospital discharge, or patient report).

```json
{
  "patient_id": "P001",
  "clinic_id": "CLINIC_A",
  "source": "clinic_emr",
  "medications": [
    {
      "name": "lisinopril",
      "dose": 10,
      "unit": "mg",
      "frequency": "daily",
      "stopped": false
    }
  ],
  "notes": "Updated from clinic visit"
}
```

**Response:** `PatientSummaryResponse` with detected conflicts.

---

### Retrieval

**GET** `/api/v1/patients/{patient_id}`

Retrieve a patient's medication summary and unresolved conflicts.

**Response:**
```json
{
  "patient_id": "P001",
  "clinic_id": "CLINIC_A",
  "last_updated": "2026-03-01T10:30:45.123Z",
  "snapshot_count": 3,
  "unresolved_conflict_count": 2,
  "conflicts": [
    {
      "conflict_type": "dose_mismatch",
      "severity": "high",
      "description": "Dose mismatch for lisinopril: 10mg, 20mg",
      "resolution_status": "unresolved",
      "detected_at": "2026-03-01T10:15:00Z"
    }
  ]
}
```

---

### Conflict Resolution

**POST** `/api/v1/conflicts/{patient_id}/{conflict_index}/resolve`

Mark a conflict as resolved.

**Query Parameters:**
- `resolution_reason` (string, required): Why the conflict was deemed acceptable
- `resolved_by` (string, required): User ID or system that resolved

**Response:**
```json
{
  "status": "success",
  "message": "Conflict resolved"
}
```

---

### Reporting

**GET** `/api/v1/reports/patients-with-conflicts`

List all patients in a clinic with ≥ min_conflicts unresolved medication conflicts.

**Query Parameters:**
- `clinic_id` (optional): Filter by clinic
- `min_conflicts` (int, default=1): Minimum number of unresolved conflicts

**Response:**
```json
{
  "count": 3,
  "patients": [
    {
      "patient_id": "P001",
      "clinic_id": "CLINIC_A",
      "last_updated": "2026-03-01T10:30:45.123Z",
      "unresolved_conflict_count": 2,
      "conflicts": [ ... ]
    }
  ]
}
```

**GET** `/api/v1/reports/conflict-summary`

Get aggregated conflict statistics by type and resolution status.

**Query Parameters:**
- `clinic_id` (optional): Filter by clinic
- `start_date` (datetime, optional): Filter conflicts detected after this date
- `end_date` (datetime, optional): Filter conflicts detected before this date

**Response:**
```json
{
  "total_patients": 15,
  "conflict_statistics": [
    {
      "_id": "dose_mismatch",
      "count": 4,
      "unresolved": 3
    },
    {
      "_id": "blacklisted_combination",
      "count": 6,
      "unresolved": 5
    }
  ]
}
```

---

## Data Model (MongoDB)

### `patients` Collection

```javascript
{
  "_id": ObjectId,
  "patient_id": "P001",
  "clinic_id": "CLINIC_A",
  "created_at": ISODate("2026-03-01T10:00:00Z"),
  "updated_at": ISODate("2026-03-01T10:30:45Z"),
  
  "snapshots": [
    {
      "source": "clinic_emr",
      "captured_at": ISODate("2026-03-01T09:00:00Z"),
      "clinic_id": "CLINIC_A",
      "notes": "...",
      "medications": [
        {
          "name": "lisinopril",
          "dose": 10,
          "unit": "mg",
          "frequency": "daily",
          "route": "oral",
          "stopped": false,
          "notes": "..."
        }
      ]
    },
    // ... more snapshots
  ],
  
  "conflicts": [
    {
      "conflict_type": "dose_mismatch",
      "sources_involved": ["clinic_emr", "hospital_discharge"],
      "drug_names": ["lisinopril"],
      "description": "Dose mismatch for lisinopril: 10mg, 20mg",
      "severity": "high",
      "detected_at": ISODate("2026-03-01T10:15:00Z"),
      "resolution_status": "unresolved",
      "resolution_reason": null,
      "resolved_by": null,
      "resolved_at": null,
      "metadata": {}
    },
    // ... more conflicts
  ]
}
```

### Indexes

```javascript
db.patients.createIndex({ "patient_id": 1 })
db.patients.createIndex({ "clinic_id": 1 })
db.patients.createIndex({ "clinic_id": 1, "updated_at": -1 })
```

---

## Conflict Detection Rules

Conflicts are defined in `data/conflict_rules.json`:

1. **Dose Mismatch**: Same drug, different doses across sources (multi-source only)
2. **Blacklisted Combinations**: Drug classes that should not be combined (ACE inhibitor + ARB, NSAID + ACE, etc.)
3. **Missing or Stopped**: Medication active in one source but stopped in another (multi-source)

### Example Rule (ACE + ARB)

Dialysis patients are at high risk of hyperkalemia when both ACE inhibitors and ARBs are present.

```json
{
  "drugs": ["ACE_INHIBITOR", "ARB"],
  "reason": "Both work on renin-angiotensin system; risk of hyperkalemia"
}
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Coverage

Tests focus on core business logic:

✅ **Conflict Detection**
- Dose mismatches across sources
- Blacklisted drug combinations
- Missing or stopped medications
- Medication name normalization
- Edge cases (empty snapshots, missing dose info, stopped meds)

✅ **Integration**
- End-to-end conflict detection flow
- Multi-conflict scenarios

### Example Test Output

```
tests/test_conflict_detection.py::TestConflictDetection::test_detect_dose_mismatch PASSED
tests/test_conflict_detection.py::TestConflictDetection::test_detect_blacklisted_combination PASSED
tests/test_conflict_detection.py::TestConflictDetection::test_detect_missing_or_stopped PASSED
tests/test_conflict_detection.py::TestEdgeCases::test_empty_snapshots PASSED
```

---

## Synthetic Dataset

The `data/seed_data.py` script generates 15 synthetic patients across 3 clinics with realistic conflicts:

- **4 patients** with dose mismatches
- **5 patients** with blacklisted drug combinations  
- **2 patients** with missing/stopped drug inconsistencies
- **4 patients** with no conflicts (baseline)

**Run the seeder:**

```bash
python data/seed_data.py
```

Output:
```
================================================================================
🔄 Seeding Medication Reconciliation Database
================================================================================

📋 Ingesting P001: John Doe (Hypertension + CKD)
   ⚠️  Found 1 conflicts
   ✅ P001 ingested

...

✅ Seeding complete!
   • Total patients: 15
   • Total ingestions: 24
   • Total conflicts found: 13
================================================================================
```

---

## Assumptions & Trade-Offs

### Assumptions

1. **Single clinic per patient** — Patients aren't transferred between clinics (PKs are patient_id, clinic_id)
2. **Conflict resolution is idempotent** — Can re-resolve the same conflict without error
3. **Snapshots are immutable** — Once ingested, snapshots aren't modified (new snapshot replaces old)
4. **Drug normalization is sufficient** — Lowercasing and trimming adequately canonicalize names
5. **Real-time consistency OK** — Not ACID-critical; periodic conflicts detected on ingestion are acceptable

### Trade-Offs

| Problem | Solution | Trade-off |
|---------|----------|-----------|
| **Document size growth** | Snapshots embedded; can delete old ones manually | Batch archival not automated; future: TTL index |
| **Conflict deduplication** | Simple string comparison of (type, drug_names) | Won't catch semantic duplicates (e.g., "lisinopril" vs "Prinivil") |
| **Single source conflicts** | Blacklist combos flagged within single source | Dose mismatches require 2+ sources (no flag when only source changes dose) |
| **Resolution tracking** | In-place update to conflict doc | No event log; can't undo resolutions (future: event sourcing) |
| **Drug database** | Static JSON file | Manual updates; no real-time drug interactions (future: RxNav/RxNorm API) |

---

## Known Limitations & Future Work

### Limitations

- ❌ No authentication/authorization (future: JWT + role-based access)
- ❌ No soft-delete for conflicts (marked resolved, not archived)
- ❌ Snapshot archival is manual (future: TTL index or cron job)
- ❌ No WebSocket for real-time conflict notifications
- ❌ Drug database is static JSON (future: RxNav API for real interactions)
- ❌ No pagination on large patient lists (future: cursor-based pagination)

### Future Enhancements

1. **Persistent conflict audit log** — Event-sourcing approach to track all resolution attempts
2. **ML-based conflict confidence** — Score conflicts by likelihood vs. false positive
3. **Real-time drug interaction database** — Integration with RxNav or similar
4. **Batch ingestion API** — CSV/FHIR upload for clinic bulk updates
5. **Mobile clinician app** — Push notifications for high-severity conflicts
6. **FHIR compliance** — Export medication lists as FHIR Medication/MedicationStatement resources
7. **Cost/benefit analysis** — Conflict resolution recommendations based on clinical guidelines
8. **Distributed tracing** — OpenTelemetry integration for production observability

---

## AI Tool Usage

### What AI Was Used For

- **Code scaffold & boilerplate** (Pydantic models, FastAPI decorators, MongoDB CRUD)
- **Conflict detection algorithm design** (brainstorming approach for multi-source comparisons)
- **Test case generation** (edge cases, realistic patient scenarios)
- **Documentation & README** (structure, examples, diagrams)

### What I Reviewed & Changed Manually

- **Naming** — Renamed ConflictRule → ConflictType for clarity; sources_involved for multi-source tracking
- **Conflict deduplication logic** — AI suggested tuple hashing; I refined to use conflict_type + drug_names
- **Database indexing** — Added clinic_id + updated_at for reporting queries (AI missed second index)
- **Error handling** — Expanded validation for malformed payloads, clinic_id consistency
- **Seed data scale** — AI generated 50 patients; I reduced to 15 for clarity and faster feedback

### Example Disagreement: Conflict Deduplication

**AI's approach:**
```python
seen = set()
for c in conflicts:
    if c.id not in seen:  # ❌ id is None for new conflicts
        seen.add(c.id)
```

**My approach:**
```python
seen = set()
for c in conflicts:
    key = (c.conflict_type, tuple(sorted(c.drug_names)))
    if key not in seen:
        seen.add(key)
        unique_conflicts.append(c)
```

I changed this because new conflictshave no ID yet; we must deduplicate by semantic content (type + drug names).

---

## Project Timeline

- **Setup & schemas** — 30 min
- **Conflict detection logic** — 90 min (3 algorithms, edge cases)
- **FastAPI endpoints** — 60 min (5 endpoints + error handling)
- **MongoDB operations** — 45 min (CRUD, aggregation pipeline)
- **Tests** — 45 min (8 test cases + integration)
- **Seed data** — 30 min (15 patients, annotation)
- **Documentation & README** — 45 min (this file)

**Total: ~5.5 hours (well within 6–10 hour budget)**

---

## Running the Service

```bash
# Terminal 1: MongoDB (if local)
mongod

# Terminal 2: FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Try the API
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"P001","clinic_id":"CLINIC_A","source":"clinic_emr","medications":[{"name":"lisinopril","dose":10,"unit":"mg"}]}'

# Or visit http://localhost:8000/docs for interactive Swagger UI
```

---

## License

MIT

---

**Questions or feedback?** Open an issue or email the maintainer.
