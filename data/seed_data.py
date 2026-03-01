"""
Synthetic data seed script for testing and demonstration.
Generates 15 patients with varied medication lists and conflicts.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timedelta
from app.models import (
    MedicationItem,
    MedicationSource,
    IngestionRequest,
)
from app.db import Database
from app.conflict_detector import ConflictDetector


def generate_synthetic_patients():
    """
    Generate 15 synthetic patients with varied medication lists and conflicts.
    """
    patients_data = [
        {
            "patient_id": "P001",
            "clinic_id": "CLINIC_A",
            "name": "John Doe",
            "condition": "Hypertension + CKD (dialysis patient)",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="lisinopril", dose=10, unit="mg", frequency="daily"),
                        MedicationItem(name="metoprolol", dose=100, unit="mg", frequency="daily"),
                    ],
                },
                {
                    "source": MedicationSource.HOSPITAL_DISCHARGE,
                    "medications": [
                        MedicationItem(name="lisinopril", dose=20, unit="mg", frequency="daily"),  # ❌ dose mismatch
                        MedicationItem(name="metoprolol", dose=100, unit="mg", frequency="daily"),
                    ],
                },
            ],
        },
        {
            "patient_id": "P002",
            "clinic_id": "CLINIC_A",
            "name": "Jane Smith",
            "condition": "Hypertension + CKD (Stage 4)",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="losartan", dose=50, unit="mg", frequency="daily"),
                        MedicationItem(name="lisinopril", dose=10, unit="mg", frequency="daily"),  # ❌ blacklist combo
                    ],
                },
            ],
        },
        {
            "patient_id": "P003",
            "clinic_id": "CLINIC_A",
            "name": "Robert Johnson",
            "condition": "Hypertension + Dialysis",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="amlodipine", dose=5, unit="mg", frequency="daily"),
                    ],
                },
                {
                    "source": MedicationSource.HOSPITAL_DISCHARGE,
                    "medications": [
                        MedicationItem(name="amlodipine", dose=5, unit="mg", stopped=True),  # ❌ present but stopped
                    ],
                },
            ],
        },
        {
            "patient_id": "P004",
            "clinic_id": "CLINIC_B",
            "name": "Mary Brown",
            "condition": "Hypertension + Pain",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="ibuprofen", dose=400, unit="mg", frequency="twice daily"),
                        MedicationItem(name="lisinopril", dose=10, unit="mg", frequency="daily"),  # ❌ blacklist combo
                    ],
                },
            ],
        },
        {
            "patient_id": "P005",
            "clinic_id": "CLINIC_B",
            "name": "David Wilson",
            "condition": "Dialysis patient - stable",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="metoprolol", dose=100, unit="mg", frequency="daily"),
                        MedicationItem(name="amlodipine", dose=5, unit="mg", frequency="daily"),
                    ],
                },
            ],
        },
        {
            "patient_id": "P006",
            "clinic_id": "CLINIC_B",
            "name": "Sandra Davis",
            "condition": "Hypertension + Renal disease",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="losartan", dose=50, unit="mg", frequency="daily"),
                        MedicationItem(name="metoprolol", dose=150, unit="mg", frequency="daily"),
                    ],
                },
                {
                    "source": MedicationSource.HOSPITAL_DISCHARGE,
                    "medications": [
                        MedicationItem(name="losartan", dose=100, unit="mg", frequency="daily"),  # ❌ dose mismatch
                        MedicationItem(name="metoprolol", dose=100, unit="mg", frequency="daily"),  # ❌ dose mismatch
                    ],
                },
            ],
        },
        {
            "patient_id": "P007",
            "clinic_id": "CLINIC_C",
            "name": "Michael Garcia",
            "condition": "Dialysis patient - stable",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="amlodipine", dose=7.5, unit="mg", frequency="daily"),
                    ],
                },
            ],
        },
        {
            "patient_id": "P008",
            "clinic_id": "CLINIC_C",
            "name": "Jennifer Martinez",
            "condition": "Hypertension + multiple comorbidities",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="naproxen", dose=500, unit="mg", frequency="twice daily"),
                        MedicationItem(name="losartan", dose=50, unit="mg", frequency="daily"),  # ❌ blacklist combo
                    ],
                },
            ],
        },
        {
            "patient_id": "P009",
            "clinic_id": "CLINIC_A",
            "name": "Christopher Lee",
            "condition": "Dialysis + Hypertension",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="diltiazem", dose=240, unit="mg", frequency="daily"),
                        MedicationItem(name="metoprolol", dose=100, unit="mg", frequency="daily"),
                    ],
                },
                {
                    "source": MedicationSource.PATIENT_REPORTED,
                    "medications": [
                        MedicationItem(name="diltiazem", dose=180, unit="mg", frequency="daily"),  # ❌ dose mismatch
                        MedicationItem(name="metoprolol", dose=100, unit="mg", frequency="daily"),
                    ],
                },
            ],
        },
        {
            "patient_id": "P010",
            "clinic_id": "CLINIC_B",
            "name": "Lisa Anderson",
            "condition": "Hypertension - well controlled",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="amlodipine", dose=5, unit="mg", frequency="daily"),
                        MedicationItem(name="lisinopril", dose=10, unit="mg", frequency="daily"),
                        MedicationItem(name="hydrochlorothiazide", dose=25, unit="mg", frequency="daily"),
                    ],
                },
            ],
        },
        {
            "patient_id": "P011",
            "clinic_id": "CLINIC_C",
            "name": "James Taylor",
            "condition": "Dialysis patient - multiple conflicts",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="lisinopril", dose=10, unit="mg", frequency="daily"),
                        MedicationItem(name="losartan", dose=50, unit="mg", frequency="daily"),  # ❌ blacklist combo
                        MedicationItem(name="ibuprofen", dose=400, unit="mg", frequency="as needed"),  # ❌ blacklist with ACE
                    ],
                },
            ],
        },
        {
            "patient_id": "P012",
            "clinic_id": "CLINIC_A",
            "name": "Patricia White",
            "condition": "CKD Stage 5 - dialysis",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="metropolol", dose=75, unit="mg", frequency="twice daily"),
                    ],
                },
                {
                    "source": MedicationSource.HOSPITAL_DISCHARGE,
                    "medications": [
                        MedicationItem(name="metoprolol", dose=150, unit="mg", frequency="daily"),  # ❌ dose mismatch
                    ],
                },
            ],
        },
        {
            "patient_id": "P013",
            "clinic_id": "CLINIC_B",
            "name": "Daniel Thomas",
            "condition": "Stable on current regimen",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="atenolol", dose=50, unit="mg", frequency="daily"),
                        MedicationItem(name="verapamil", dose=120, unit="mg", frequency="twice daily"),
                    ],
                },
            ],
        },
        {
            "patient_id": "P014",
            "clinic_id": "CLINIC_C",
            "name": "Barbara Harris",
            "condition": "Hypertension + CKD",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="ramipril", dose=5, unit="mg", frequency="daily"),
                        MedicationItem(name="valsartan", dose=80, unit="mg", frequency="daily"),  # ❌ blacklist combo (ACE + ARB)
                    ],
                },
            ],
        },
        {
            "patient_id": "P015",
            "clinic_id": "CLINIC_A",
            "name": "Mark Jackson",
            "condition": "Hypertension - on indomethacin",
            "sources": [
                {
                    "source": MedicationSource.CLINIC_EMR,
                    "medications": [
                        MedicationItem(name="indomethacin", dose=50, unit="mg", frequency="twice daily"),
                        MedicationItem(name="enalapril", dose=10, unit="mg", frequency="daily"),  # ❌ blacklist combo (NSAID + ACE)
                    ],
                },
            ],
        },
    ]
    
    return patients_data


def seed_database():
    """
    Load synthetic patients into the database.
    """
    db = Database()
    detector = ConflictDetector()
    
    patients_data = generate_synthetic_patients()
    
    print(f"\n{'='*80}")
    print("🔄 Seeding Medication Reconciliation Database")
    print(f"{'='*80}\n")
    
    ingested_count = 0
    total_conflicts = 0
    
    for patient_data in patients_data:
        patient_id = patient_data["patient_id"]
        clinic_id = patient_data["clinic_id"]
        
        print(f"📋 Ingesting {patient_id}: {patient_data['name']} ({patient_data['condition']})")
        
        for source_data in patient_data["sources"]:
            request = IngestionRequest(
                patient_id=patient_id,
                clinic_id=clinic_id,
                source=source_data["source"],
                medications=source_data["medications"],
                notes=f"Seeded data for {patient_data['name']} from {source_data['source'].value}",
            )
            
            # Normalize medication names
            for med in request.medications:
                med.name = detector.normalize_medication_name(med.name)
            
            # Get or create patient record
            patient = db.get_patient_record(patient_id)
            
            if patient is None:
                from app.models import PatientMedicationRecord
                patient = PatientMedicationRecord(
                    patient_id=patient_id,
                    clinic_id=clinic_id,
                    snapshots=[],
                    conflicts=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            
            # Create snapshot
            from app.models import MedicationSnapshot
            snapshot = MedicationSnapshot(
                source=request.source,
                medications=request.medications,
                captured_at=datetime.utcnow(),
                clinic_id=request.clinic_id,
                notes=request.notes,
            )
            
            patient.snapshots.append(snapshot)
            
            # Detect conflicts
            conflicts = detector.detect_all_conflicts(patient.snapshots)
            
            # Only keep new conflicts
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
            
            ingested_count += 1
            unresolved = [c for c in new_conflicts if c.resolution_status.value == "unresolved"]
            if unresolved:
                total_conflicts += len(unresolved)
                print(f"   ⚠️  Found {len(unresolved)} conflicts")
        
        print(f"   ✅ {patient_id} ingested")
        print()
    
    print(f"\n{'='*80}")
    print(f"✅ Seeding complete!")
    print(f"   • Total patients: {len(patients_data)}")
    print(f"   • Total ingestions: {ingested_count}")
    print(f"   • Total conflicts found: {total_conflicts}")
    print(f"{'='*80}\n")
    
    # Show summary by clinic
    print("📊 Summary by clinic:")
    clinics = {}
    for patient_data in patients_data:
        clinic = patient_data["clinic_id"]
        if clinic not in clinics:
            clinics[clinic] = 0
        clinics[clinic] += 1
    
    for clinic, count in sorted(clinics.items()):
        print(f"   • {clinic}: {count} patients")
    
    db.close()


if __name__ == "__main__":
    seed_database()
