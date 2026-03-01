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
    CLINIC_EMR,
    HOSPITAL_DISCHARGE,
    PATIENT_REPORTED,
    createMedItem,
    createIngestReq,
    createPatMedRec,
    createMedSnap,
)
from app.db import Database
from app.conflDetect import ConflictDetector


def genSynthPats():
    """
    Generate 15 synthetic patients with varied medication lists and conflicts.
    """
    patsData = [
        {
            "patId": "P001",
            "clinId": "CLINIC_A",
            "name": "John Doe",
            "condition": "Hypertension + CKD (dialysis patient)",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="lisinopril", dose=10, unit="mg", freq="daily"),
                        createMedItem(name="metoprolol", dose=100, unit="mg", freq="daily"),
                    ],
                },
                {
                    "src": HOSPITAL_DISCHARGE,
                    "meds": [
                        createMedItem(name="lisinopril", dose=20, unit="mg", freq="daily"),
                        createMedItem(name="metoprolol", dose=100, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P002",
            "clinId": "CLINIC_A",
            "name": "Jane Smith",
            "condition": "Hypertension + CKD (Stage 4)",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="losartan", dose=50, unit="mg", freq="daily"),
                        createMedItem(name="lisinopril", dose=10, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P003",
            "clinId": "CLINIC_A",
            "name": "Robert Johnson",
            "condition": "Hypertension + Dialysis",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="amlodipine", dose=5, unit="mg", freq="daily"),
                    ],
                },
                {
                    "src": HOSPITAL_DISCHARGE,
                    "meds": [
                        createMedItem(name="amlodipine", dose=5, unit="mg", stopped=True),
                    ],
                },
            ],
        },
        {
            "patId": "P004",
            "clinId": "CLINIC_B",
            "name": "Mary Brown",
            "condition": "Hypertension + Pain",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="ibuprofen", dose=400, unit="mg", freq="twice daily"),
                        createMedItem(name="lisinopril", dose=10, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P005",
            "clinId": "CLINIC_B",
            "name": "David Wilson",
            "condition": "Dialysis patient - stable",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="metoprolol", dose=100, unit="mg", freq="daily"),
                        createMedItem(name="amlodipine", dose=5, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P006",
            "clinId": "CLINIC_B",
            "name": "Sandra Davis",
            "condition": "Hypertension + Renal disease",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="losartan", dose=50, unit="mg", freq="daily"),
                        createMedItem(name="metoprolol", dose=150, unit="mg", freq="daily"),
                    ],
                },
                {
                    "src": HOSPITAL_DISCHARGE,
                    "meds": [
                        createMedItem(name="losartan", dose=100, unit="mg", freq="daily"),
                        createMedItem(name="metoprolol", dose=100, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P007",
            "clinId": "CLINIC_C",
            "name": "Michael Garcia",
            "condition": "Dialysis patient - stable",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="amlodipine", dose=7.5, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P008",
            "clinId": "CLINIC_C",
            "name": "Jennifer Martinez",
            "condition": "Hypertension + multiple comorbidities",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="naproxen", dose=500, unit="mg", freq="twice daily"),
                        createMedItem(name="losartan", dose=50, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P009",
            "clinId": "CLINIC_A",
            "name": "Christopher Lee",
            "condition": "Dialysis + Hypertension",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="diltiazem", dose=240, unit="mg", freq="daily"),
                        createMedItem(name="metoprolol", dose=100, unit="mg", freq="daily"),
                    ],
                },
                {
                    "src": PATIENT_REPORTED,
                    "meds": [
                        createMedItem(name="diltiazem", dose=180, unit="mg", freq="daily"),
                        createMedItem(name="metoprolol", dose=100, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P010",
            "clinId": "CLINIC_B",
            "name": "Lisa Anderson",
            "condition": "Hypertension - well controlled",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="amlodipine", dose=5, unit="mg", freq="daily"),
                        createMedItem(name="lisinopril", dose=10, unit="mg", freq="daily"),
                        createMedItem(name="hydrochlorothiazide", dose=25, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P011",
            "clinId": "CLINIC_C",
            "name": "James Taylor",
            "condition": "Dialysis patient - multiple conflicts",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="lisinopril", dose=10, unit="mg", freq="daily"),
                        createMedItem(name="losartan", dose=50, unit="mg", freq="daily"),
                        createMedItem(name="ibuprofen", dose=400, unit="mg", freq="as needed"),
                    ],
                },
            ],
        },
        {
            "patId": "P012",
            "clinId": "CLINIC_A",
            "name": "Patricia White",
            "condition": "CKD Stage 5 - dialysis",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="metropolol", dose=75, unit="mg", freq="twice daily"),
                    ],
                },
                {
                    "src": HOSPITAL_DISCHARGE,
                    "meds": [
                        createMedItem(name="metoprolol", dose=150, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P013",
            "clinId": "CLINIC_B",
            "name": "Daniel Thomas",
            "condition": "Stable on current regimen",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="atenolol", dose=50, unit="mg", freq="daily"),
                        createMedItem(name="verapamil", dose=120, unit="mg", freq="twice daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P014",
            "clinId": "CLINIC_C",
            "name": "Barbara Harris",
            "condition": "Hypertension + CKD",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="ramipril", dose=5, unit="mg", freq="daily"),
                        createMedItem(name="valsartan", dose=80, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
        {
            "patId": "P015",
            "clinId": "CLINIC_A",
            "name": "Mark Jackson",
            "condition": "Hypertension - on indomethacin",
            "srcs": [
                {
                    "src": CLINIC_EMR,
                    "meds": [
                        createMedItem(name="indomethacin", dose=50, unit="mg", freq="twice daily"),
                        createMedItem(name="enalapril", dose=10, unit="mg", freq="daily"),
                    ],
                },
            ],
        },
    ]
    
    return patsData


def seedDB():
    """Load synthetic patients into the database."""
    db = Database()
    detector = ConflictDetector()
    
    patsData = genSynthPats()
    
    print(f"\n{'='*80}")
    print("🔄 Seeding Medication Reconciliation Database")
    print(f"{'='*80}\n")
    
    ingestedCnt = 0
    totalConfs = 0
    
    for patData in patsData:
        patId = patData["patId"]
        clinId = patData["clinId"]
        
        print(f"📋 Ingesting {patId}: {patData['name']} ({patData['condition']})")
        
        for srcData in patData["srcs"]:
            src = srcData["src"]
            meds = srcData["meds"]
            
            for med in meds:
                med['name'] = detector.normMedName(med['name'])
            
            pat = db.getPatRec(patId)
            
            if pat is None:
                pat = createPatMedRec(
                    patId=patId,
                    clinId=clinId,
                    snaps=[],
                    confs=[],
                    creatAt=datetime.now(timezone.utc),
                    updatAt=datetime.now(timezone.utc),
                )
            
            snap = createMedSnap(
                src=src,
                meds=meds,
                capturAt=datetime.now(timezone.utc),
                clinId=clinId,
                notes=f"Seeded data for {patData['name']} from {src}",
            )
            
            pat['snaps'].append(snap)
            
            confs = detector.detectAllConf(pat['snaps'])
            
            existConfDesc = {
                (c.get('confType'), tuple(sorted(c.get('drugNames', []))))
                for c in pat['confs']
            }
            
            newConfs = [
                c for c in confs
                if (c.get('confType'), tuple(sorted(c.get('drugNames', [])))) not in existConfDesc
            ]
            
            pat['confs'].extend(newConfs)
            pat['updatAt'] = datetime.now(timezone.utc)
            
            db.upsertPatRec(pat)
            
            ingestedCnt += 1
            unres = [c for c in newConfs if c.get('resoStatus') == "unresolved"]
            if unres:
                totalConfs += len(unres)
                print(f"   ⚠️  Found {len(unres)} conflicts")
        
        print(f"   ✅ {patId} ingested")
        print()
    
    print(f"\n{'='*80}")
    print(f"✅ Seeding complete!")
    print(f"   • Total patients: {len(patsData)}")
    print(f"   • Total ingestions: {ingestedCnt}")
    print(f"   • Total conflicts found: {totalConfs}")
    print(f"{'='*80}\n")
    
    print("📊 Summary by clinic:")
    clinics = {}
    for patData in patsData:
        clinic = patData["clinId"]
        if clinic not in clinics:
            clinics[clinic] = 0
        clinics[clinic] += 1
    
    for clinic, cnt in sorted(clinics.items()):
        print(f"   • {clinic}: {cnt} patients")
    
    db.close()


if __name__ == "__main__":
    seedDB()
