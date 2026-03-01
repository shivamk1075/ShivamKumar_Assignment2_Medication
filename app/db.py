"""
MongoDB database operations and connection management.
"""
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from .models import (
    PatientMedicationRecord,
    MedicationSnapshot,
    MedicationConflict,
)


class Database:
    """MongoDB database operations."""

    def __init__(self, connection_string: str = None):
        """
        Initialize database connection.
        
        Args:
            connection_string: MongoDB connection string. 
                             Defaults to MONGODB_URL env var or local instance.
        """
        if connection_string is None:
            connection_string = os.getenv(
                "MONGODB_URL", "mongodb://localhost:27017"
            )
        
        self.client = MongoClient(connection_string)
        self.db = self.client["medication_reconciliation"]
        self._setup_collections()
    
    def _setup_collections(self):
        """Set up collections and indexes."""
        # Create collections if they don't exist
        if "patients" not in self.db.list_collection_names():
            self.db.create_collection("patients")
        
        # Create indexes
        self.patients.create_index("patient_id")
        self.patients.create_index("clinic_id")
        self.patients.create_index([("clinic_id", 1), ("updated_at", -1)])
    
    @property
    def patients(self) -> Collection:
        """Get patients collection."""
        return self.db["patients"]
    
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
        
        result = self.patients.update_one(
            {"patient_id": record.patient_id},
            {"$set": record.model_dump()},
            upsert=True,
        )
        
        return record.patient_id
    
    def get_patient_record(self, patient_id: str) -> Optional[PatientMedicationRecord]:
        """Retrieve a patient's medication record."""
        doc = self.patients.find_one({"patient_id": patient_id})
        if doc:
            doc.pop("_id", None)
            return PatientMedicationRecord(**doc)
        return None
    
    def add_snapshot(
        self, patient_id: str, snapshot: MedicationSnapshot
    ) -> None:
        """Add a medication snapshot to a patient's record."""
        self.patients.update_one(
            {"patient_id": patient_id},
            {
                "$push": {"snapshots": snapshot.model_dump()},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
    
    def add_conflicts(
        self, patient_id: str, conflicts: List[MedicationConflict]
    ) -> None:
        """Add detected conflicts to a patient's record."""
        if not conflicts:
            return
        
        self.patients.update_one(
            {"patient_id": patient_id},
            {
                "$push": {"conflicts": {"$each": [c.model_dump() for c in conflicts]}},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
    
    def resolve_conflict(
        self,
        patient_id: str,
        conflict_index: int,
        resolution_reason: str,
        resolved_by: str,
    ) -> None:
        """Mark a conflict as resolved."""
        self.patients.update_one(
            {"patient_id": patient_id},
            {
                "$set": {
                    f"conflicts.{conflict_index}.resolution_status": "resolved",
                    f"conflicts.{conflict_index}.resolution_reason": resolution_reason,
                    f"conflicts.{conflict_index}.resolved_by": resolved_by,
                    f"conflicts.{conflict_index}.resolved_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
    
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
        query = {
            "conflicts": {
                "$elemMatch": {
                    "resolution_status": "unresolved"
                }
            }
        }
        
        if clinic_id:
            query["clinic_id"] = clinic_id
        
        docs = self.patients.find(query)
        
        results = []
        for doc in docs:
            doc.pop("_id", None)
            record = PatientMedicationRecord(**doc)
            
            # Filter to only unresolved conflicts
            unresolved = [
                c for c in record.conflicts
                if c.resolution_status == "unresolved"
            ]
            
            if len(unresolved) >= min_conflicts:
                record.conflicts = unresolved
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
        match_stage = {}
        
        if clinic_id:
            match_stage["clinic_id"] = clinic_id
        
        pipeline = [
            {"$match": match_stage},
            {"$unwind": "$conflicts"},
            {
                "$group": {
                    "_id": "$conflicts.conflict_type",
                    "count": {"$sum": 1},
                    "unresolved": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$conflicts.resolution_status", "unresolved"]},
                                1,
                                0,
                            ]
                        }
                    },
                }
            },
        ]
        
        results = list(self.patients.aggregate(pipeline))
        
        return {
            "total_patients": self.patients.count_documents(match_stage or {}),
            "conflict_statistics": results,
        }
    
    def close(self):
        """Close database connection."""
        self.client.close()
