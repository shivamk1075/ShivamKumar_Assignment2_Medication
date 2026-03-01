"""
Pydantic models and MongoDB document definitions for medication reconciliation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class MedicationSource(str, Enum):
    """Enumeration of medication source types."""
    CLINIC_EMR = "clinic_emr"
    HOSPITAL_DISCHARGE = "hospital_discharge"
    PATIENT_REPORTED = "patient_reported"


class ConflictType(str, Enum):
    """Types of conflicts detected between medication sources."""
    DOSE_MISMATCH = "dose_mismatch"
    BLACKLISTED_COMBINATION = "blacklisted_combination"
    MISSING_STOPPED = "missing_stopped"
    DIFFERENT_FORMULATION = "different_formulation"


class ResolutionStatus(str, Enum):
    """Status of conflict resolution."""
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class MedicationItem(BaseModel):
    """Individual medication details."""
    name: str = Field(..., description="Medication name (will be normalized)")
    dose: Optional[float] = Field(None, description="Dose amount")
    unit: Optional[str] = Field(None, description="Dose unit (mg, mcg, etc.)")
    frequency: Optional[str] = Field(None, description="Dosing frequency")
    route: Optional[str] = Field(None, description="Route of administration")
    stopped: bool = Field(False, description="Whether medication is stopped")
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        use_enum_values = False


class MedicationSnapshot(BaseModel):
    """A snapshot of medications from a single source at a point in time."""
    source: MedicationSource
    medications: List[MedicationItem]
    captured_at: datetime
    clinic_id: Optional[str] = Field(None, description="Clinic identifier if applicable")
    notes: Optional[str] = None

    class Config:
        use_enum_values = False


class MedicationConflict(BaseModel):
    """Represents a conflict between medications across sources."""
    conflict_type: ConflictType
    sources_involved: List[MedicationSource]
    drug_names: List[str] = Field(description="Normalized drug names involved")
    description: str
    severity: str = Field(default="medium", description="low, medium, high")
    detected_at: datetime
    resolution_status: ResolutionStatus = Field(default=ResolutionStatus.UNRESOLVED)
    resolution_reason: Optional[str] = None
    resolved_by: Optional[str] = Field(None, description="User ID or system that resolved")
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = False


class PatientMedicationRecord(BaseModel):
    """Complete patient medication record with history."""
    patient_id: str
    clinic_id: str
    snapshots: List[MedicationSnapshot] = Field(default_factory=list)
    conflicts: List[MedicationConflict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = False


# Request/Response DTOs for API


class IngestionRequest(BaseModel):
    """Request to ingest medications from a source."""
    patient_id: str
    clinic_id: str
    source: MedicationSource
    medications: List[MedicationItem]
    notes: Optional[str] = None

    class Config:
        use_enum_values = True


class ConflictResponse(BaseModel):
    """Response model for a conflict."""
    id: Optional[str] = None
    conflict_type: str
    severity: str
    description: str
    resolution_status: str
    detected_at: datetime

    class Config:
        use_enum_values = True


class PatientSummaryResponse(BaseModel):
    """Summary response for a patient."""
    patient_id: str
    clinic_id: str
    last_updated: datetime
    snapshot_count: int
    unresolved_conflict_count: int
    conflicts: List[ConflictResponse]

    class Config:
        use_enum_values = True


class ReportingQuery(BaseModel):
    """Query parameters for reporting endpoints."""
    clinic_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_conflicts: int = Field(default=1, ge=1)
