"""
FastAPI application for medication reconciliation and conflict reporting.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .models import (
    IngestionRequest,
    PatientSummaryResponse,
    ConflictResponse,
    ReportingQuery,
    MedicationSnapshot,
    ResolutionStatus,
)
from .db import Database
from .conflict_detector import ConflictDetector


# Initialize FastAPI app
app = FastAPI(
    title="Medication Reconciliation Service",
    description="Backend service for reconciling medications across multiple sources and detecting conflicts.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and conflict detector
db = Database()
detector = ConflictDetector()


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown."""
    db.close()


# ============================================================================
# Ingestion Endpoints
# ============================================================================


@app.post("/api/v1/ingest", response_model=PatientSummaryResponse)
async def ingest_medication_list(request: IngestionRequest) -> PatientSummaryResponse:
    """
    Ingest a medication list from a source.
    
    Creates or updates a patient record with the new medication snapshot.
    Automatically detects conflicts with existing snapshots.
    
    Args:
        request: IngestionRequest with patient_id, clinic_id, source, and medications.
    
    Returns:
        PatientSummaryResponse with updated patient summary and conflicts.
    """
    try:
        # Normalize medication names
        for med in request.medications:
            med.name = detector.normalize_medication_name(med.name)
        
        # Get or create patient record
        patient = db.get_patient_record(request.patient_id)
        
        if patient is None:
            patient = PatientMedicationRecord(
                patient_id=request.patient_id,
                clinic_id=request.clinic_id,
                snapshots=[],
                conflicts=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        else:
            # Validate clinic_id consistency
            if patient.clinic_id != request.clinic_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Patient {request.patient_id} is registered at clinic "
                           f"{patient.clinic_id}, not {request.clinic_id}",
                )
        
        # Create snapshot
        snapshot = MedicationSnapshot(
            source=request.source,
            medications=request.medications,
            captured_at=datetime.utcnow(),
            clinic_id=request.clinic_id,
            notes=request.notes,
        )
        
        # Add snapshot to patient record
        patient.snapshots.append(snapshot)
        
        # Detect conflicts
        conflicts = detector.detect_all_conflicts(patient.snapshots)
        
        # Only keep new conflicts (not already in the record)
        existing_conflict_desc = {
            (c.conflict_type, tuple(sorted(c.drug_names)))
            for c in patient.conflicts
        }
        
        new_conflicts = [
            c for c in conflicts
            if (c.conflict_type, tuple(sorted(c.drug_names))) not in existing_conflict_desc
        ]
        
        patient.conflicts.extend(new_conflicts)
        patient.updated_at = datetime.utcnow()
        
        # Save to database
        db.upsert_patient_record(patient)
        
        # Build response
        unresolved = [
            c for c in patient.conflicts
            if c.resolution_status == ResolutionStatus.UNRESOLVED.value
        ]
        
        return PatientSummaryResponse(
            patient_id=patient.patient_id,
            clinic_id=patient.clinic_id,
            last_updated=patient.updated_at,
            snapshot_count=len(patient.snapshots),
            unresolved_conflict_count=len(unresolved),
            conflicts=[
                ConflictResponse(
                    conflict_type=c.conflict_type.value,
                    severity=c.severity,
                    description=c.description,
                    resolution_status=c.resolution_status.value,
                    detected_at=c.detected_at,
                )
                for c in unresolved
            ],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ingestion failed: {str(e)}")


# ============================================================================
# Retrieval Endpoints
# ============================================================================


@app.get("/api/v1/patients/{patient_id}", response_model=PatientSummaryResponse)
async def get_patient_summary(patient_id: str) -> PatientSummaryResponse:
    """
    Get a summary of a patient's medications and conflicts.
    
    Args:
        patient_id: The patient identifier.
    
    Returns:
        PatientSummaryResponse with patient info and conflicts.
    """
    patient = db.get_patient_record(patient_id)
    
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    
    unresolved = [
        c for c in patient.conflicts
        if c.resolution_status == ResolutionStatus.UNRESOLVED.value
    ]
    
    return PatientSummaryResponse(
        patient_id=patient.patient_id,
        clinic_id=patient.clinic_id,
        last_updated=patient.updated_at,
        snapshot_count=len(patient.snapshots),
        unresolved_conflict_count=len(unresolved),
        conflicts=[
            ConflictResponse(
                conflict_type=c.conflict_type.value,
                severity=c.severity,
                description=c.description,
                resolution_status=c.resolution_status.value,
                detected_at=c.detected_at,
            )
            for c in unresolved
        ],
    )


@app.post("/api/v1/conflicts/{patient_id}/{conflict_index}/resolve")
async def resolve_conflict(
    patient_id: str,
    conflict_index: int,
    resolution_reason: str = Query(..., description="Why this conflict is resolved"),
    resolved_by: str = Query(..., description="User ID or system that resolved"),
):
    """
    Mark a conflict as resolved.
    
    Args:
        patient_id: Patient identifier.
        conflict_index: Index of conflict in conflicts array.
        resolution_reason: Reason for resolution.
        resolved_by: User or system that resolved.
    
    Returns:
        Success message.
    """
    patient = db.get_patient_record(patient_id)
    
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    
    if conflict_index < 0 or conflict_index >= len(patient.conflicts):
        raise HTTPException(status_code=400, detail="Invalid conflict index")
    
    db.resolve_conflict(patient_id, conflict_index, resolution_reason, resolved_by)
    
    return {"status": "success", "message": "Conflict resolved"}


# ============================================================================
# Reporting / Aggregation Endpoints
# ============================================================================


@app.get("/api/v1/reports/patients-with-conflicts")
async def report_patients_with_conflicts(
    clinic_id: Optional[str] = Query(None, description="Filter by clinic"),
    min_conflicts: int = Query(
        1, ge=1, description="Minimum number of unresolved conflicts"
    ),
):
    """
    List patients with unresolved medication conflicts.
    
    This endpoint returns all patients in a clinic (or globally) that have
    at least the specified number of unresolved conflicts.
    
    Args:
        clinic_id: Optional clinic identifier to filter by.
        min_conflicts: Minimum number of unresolved conflicts (default: 1).
    
    Returns:
        List of patients with their conflict counts and details.
    """
    try:
        patients = db.find_patients_with_unresolved_conflicts(
            clinic_id=clinic_id,
            min_conflicts=min_conflicts,
        )
        
        return {
            "count": len(patients),
            "patients": [
                {
                    "patient_id": p.patient_id,
                    "clinic_id": p.clinic_id,
                    "last_updated": p.updated_at,
                    "unresolved_conflict_count": len(p.conflicts),
                    "conflicts": [
                        {
                            "type": c.conflict_type.value,
                            "severity": c.severity,
                            "description": c.description,
                            "detected_at": c.detected_at,
                        }
                        for c in p.conflicts
                    ],
                }
                for p in patients
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Report generation failed: {str(e)}")


@app.get("/api/v1/reports/conflict-summary")
async def report_conflict_summary(
    clinic_id: Optional[str] = Query(None, description="Filter by clinic"),
    start_date: Optional[datetime] = Query(None, description="Start date for conflict detection"),
    end_date: Optional[datetime] = Query(None, description="End date for conflict detection"),
):
    """
    Get aggregated conflict statistics.
    
    Returns summary statistics about conflicts by type, resolution status, etc.
    
    Args:
        clinic_id: Optional clinic filter.
        start_date: Optional start date for filtering.
        end_date: Optional end date for filtering.
    
    Returns:
        Dictionary with conflict statistics.
    """
    try:
        summary = db.get_conflict_summary(
            clinic_id=clinic_id,
            start_date=start_date,
            end_date=end_date,
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Report generation failed: {str(e)}")


# ============================================================================
# Health Check
# ============================================================================


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Medication Reconciliation Service",
        "version": "1.0.0",
    }
