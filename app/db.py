"""
SQLite3 database operations for medication reconciliation.
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .models import (
    PatientMedicationRecord,
    MedicationSnapshot,
    MedicationConflict,
)


class Database:
    """SQLite3 database operations."""

    def __init__(self, db_path: str = None):
        """
        Initialize SQLite database connection.
        
        Args:
            db_path: Path to SQLite database file.
                    Defaults to medication_reconciliation.db
        """
        if db_path is None:
            db_path = os.getenv(
                "SQLITE_DB_PATH", "medication_reconciliation.db"
            )
        
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._setup_tables()
    
    def _setup_tables(self):
        """Set up tables and indexes."""
        cursor = self.conn.cursor()
        
        # Create patients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                clinic_id TEXT NOT NULL,
                snapshots_json TEXT NOT NULL,
                conflicts_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clinic_id 
            ON patients(clinic_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clinic_updated 
            ON patients(clinic_id, updated_at)
        """)
        
        self.conn.commit()
    
    def upsert_patient_record(
        self, record: PatientMedicationRecord
    ) -> str:
        """
        Upsert a patient medication record.
        
        Args:
            record: PatientMedicationRecord to save.
        
        Returns:
            The patient_id.
        """
        record.updated_at = datetime.utcnow()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO patients
            (patient_id, clinic_id, snapshots_json, conflicts_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            record.patient_id,
            record.clinic_id,
            json.dumps([s.model_dump(mode='json') for s in record.snapshots]),
            json.dumps([c.model_dump(mode='json') for c in record.conflicts]),
            record.created_at.isoformat(),
            record.updated_at.isoformat(),
        ))
        
        self.conn.commit()
        return record.patient_id
    
    def get_patient_record(self, patient_id: str) -> Optional[PatientMedicationRecord]:
        """Retrieve a patient's medication record."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM patients WHERE patient_id = ?",
            (patient_id,)
        )
        row = cursor.fetchone()
        
        if row:
            snapshots_data = json.loads(row['snapshots_json'])
            conflicts_data = json.loads(row['conflicts_json'])
            
            # Parse datetime strings in snapshots
            for s in snapshots_data:
                if isinstance(s['captured_at'], str):
                    s['captured_at'] = datetime.fromisoformat(s['captured_at'])
            
            # Parse datetime strings in conflicts
            for c in conflicts_data:
                if isinstance(c['detected_at'], str):
                    c['detected_at'] = datetime.fromisoformat(c['detected_at'])
                if c.get('resolved_at') and isinstance(c['resolved_at'], str):
                    c['resolved_at'] = datetime.fromisoformat(c['resolved_at'])
            
            snapshots = [MedicationSnapshot(**s) for s in snapshots_data]
            conflicts = [MedicationConflict(**c) for c in conflicts_data]
            
            created_at = datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at']
            updated_at = datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
            
            return PatientMedicationRecord(
                patient_id=row['patient_id'],
                clinic_id=row['clinic_id'],
                snapshots=snapshots,
                conflicts=conflicts,
                created_at=created_at,
                updated_at=updated_at,
            )
        return None
    
    def add_snapshot(
        self, patient_id: str, snapshot: MedicationSnapshot
    ) -> None:
        """Add a medication snapshot to a patient's record."""
        patient = self.get_patient_record(patient_id)
        if patient:
            patient.snapshots.append(snapshot)
            patient.updated_at = datetime.utcnow()
            self.upsert_patient_record(patient)
    
    def add_conflicts(
        self, patient_id: str, conflicts: List[MedicationConflict]
    ) -> None:
        """Add detected conflicts to a patient's record."""
        if not conflicts:
            return
        
        patient = self.get_patient_record(patient_id)
        if patient:
            patient.conflicts.extend(conflicts)
            patient.updated_at = datetime.utcnow()
            self.upsert_patient_record(patient)
    
    def resolve_conflict(
        self,
        patient_id: str,
        conflict_index: int,
        resolution_reason: str,
        resolved_by: str,
    ) -> None:
        """Mark a conflict as resolved."""
        patient = self.get_patient_record(patient_id)
        if patient and 0 <= conflict_index < len(patient.conflicts):
            conflict = patient.conflicts[conflict_index]
            conflict.resolution_status = "resolved"
            conflict.resolution_reason = resolution_reason
            conflict.resolved_by = resolved_by
            conflict.resolved_at = datetime.utcnow()
            patient.updated_at = datetime.utcnow()
            self.upsert_patient_record(patient)
    
    def find_patients_with_unresolved_conflicts(
        self,
        clinic_id: Optional[str] = None,
        min_conflicts: int = 1,
    ) -> List[PatientMedicationRecord]:
        """
        Find patients with unresolved conflicts.
        
        Args:
            clinic_id: Filter by clinic (optional).
            min_conflicts: Minimum number of unresolved conflicts.
        
        Returns:
            List of PatientMedicationRecord.
        """
        cursor = self.conn.cursor()
        
        if clinic_id:
            cursor.execute("SELECT * FROM patients WHERE clinic_id = ?", (clinic_id,))
        else:
            cursor.execute("SELECT * FROM patients")
        
        rows = cursor.fetchall()
        results = []
        
        for row in rows:
            snapshots_data = json.loads(row['snapshots_json'])
            conflicts_data = json.loads(row['conflicts_json'])
            
            # Parse datetime strings
            for s in snapshots_data:
                if isinstance(s['captured_at'], str):
                    s['captured_at'] = datetime.fromisoformat(s['captured_at'])
            
            for c in conflicts_data:
                if isinstance(c['detected_at'], str):
                    c['detected_at'] = datetime.fromisoformat(c['detected_at'])
                if c.get('resolved_at') and isinstance(c['resolved_at'], str):
                    c['resolved_at'] = datetime.fromisoformat(c['resolved_at'])
            
            snapshots = [MedicationSnapshot(**s) for s in snapshots_data]
            conflicts = [MedicationConflict(**c) for c in conflicts_data]
            
            # Filter to only unresolved conflicts
            unresolved = [c for c in conflicts if c.resolution_status == "unresolved"]
            
            if len(unresolved) >= min_conflicts:
                created_at = datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at']
                updated_at = datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
                
                record = PatientMedicationRecord(
                    patient_id=row['patient_id'],
                    clinic_id=row['clinic_id'],
                    snapshots=snapshots,
                    conflicts=unresolved,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                results.append(record)
        
        return results
    
    def get_conflict_summary(
        self,
        clinic_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated conflict statistics.
        
        Args:
            clinic_id: Optional clinic filter.
            start_date: Optional start date for detected_at.
            end_date: Optional end date for detected_at.
        
        Returns:
            Dictionary with summary statistics.
        """
        cursor = self.conn.cursor()
        
        # Get all patients
        if clinic_id:
            cursor.execute("SELECT * FROM patients WHERE clinic_id = ?", (clinic_id,))
        else:
            cursor.execute("SELECT * FROM patients")
        
        rows = cursor.fetchall()
        
        total_patients = len(rows)
        conflict_stats = {}
        
        for row in rows:
            conflicts_data = json.loads(row['conflicts_json'])
            
            # Parse datetime strings
            for c in conflicts_data:
                if isinstance(c['detected_at'], str):
                    c['detected_at'] = datetime.fromisoformat(c['detected_at'])
                if c.get('resolved_at') and isinstance(c['resolved_at'], str):
                    c['resolved_at'] = datetime.fromisoformat(c['resolved_at'])
            
            conflicts = [MedicationConflict(**c) for c in conflicts_data]
            
            for conflict in conflicts:
                conflict_type = conflict.conflict_type
                
                if conflict_type not in conflict_stats:
                    conflict_stats[conflict_type] = {"count": 0, "unresolved": 0}
                
                conflict_stats[conflict_type]["count"] += 1
                if conflict.resolution_status == "unresolved":
                    conflict_stats[conflict_type]["unresolved"] += 1
        
        return {
            "total_patients": total_patients,
            "conflict_statistics": [
                {"_id": k, **v} for k, v in conflict_stats.items()
            ]
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()
