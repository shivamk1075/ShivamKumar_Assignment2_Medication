"""
FastAPI application for medication reconciliation.
"""
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from .models import (
    CLINIC_EMR,
    HOSPITAL_DISCHARGE,
    PATIENT_REPORTED,
    MEDICATION_SOURCES,
    UNRESOLVED,
    RESOLVED,
    createMedSnap,
    createPatMedRec,
    createConfResp,
    createPatSummResp,
)
from .db import Database
from .conflDetect import ConflictDetector


app = FastAPI(
    title="Medication Reconciliation Service",
    description="Backend service for reconciling medications across multiple sources and detecting conflicts.",
    version="1.0.0",
)

db = Database()
detector = ConflictDetector()





@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown."""
    db.close()




@app.post("/ingest")
async def ingestMedList(req: dict):
    """
    Ingest medications from a source.
    
    Creates/updates patient record with new snapshot.
    Automatically detects conflicts.
    """
    try:
        patId = req.get('patId')
        clinId = req.get('clinId')
        src = req.get('src')
        meds = req.get('meds', [])
        notes = req.get('notes')
        
        if not patId or not clinId or not src or not meds:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        if src not in MEDICATION_SOURCES:
            raise HTTPException(status_code=400, detail=f"Invalid source: {src}")
        
        for med in meds:
            if isinstance(med, dict) and 'name' in med:
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
        else:
            if pat.get('clinId') != clinId:
                raise HTTPException(
                    status_code=400,
                    detail=f"Patient {patId} is registered at clinic "
                           f"{pat.get('clinId')}, not {clinId}",
                )
        
        snap = createMedSnap(
            src=src,
            meds=meds,
            capturAt=datetime.now(timezone.utc),
            clinId=clinId,
            notes=notes,
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
        
        unres = [
            c for c in pat['confs']
            if c.get('resoStatus') == UNRESOLVED
        ]
        
        confResp = [
            createConfResp(
                confType=c.get('confType'),
                severity=c.get('severity'),
                desc=c.get('desc'),
                resoStatus=c.get('resoStatus'),
                detectAt=c.get('detectAt'),
                id=c.get('id'),
            )
            for c in unres
        ]
        
        resp = createPatSummResp(
            patId=pat.get('patId'),
            clinId=pat.get('clinId'),
            lastUpdated=pat.get('updatAt'),
            snapCnt=len(pat.get('snaps', [])),
            unresolConfCnt=len(unres),
            confs=confResp,
        )
        
        return resp
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ingestion failed: {str(e)}")



@app.get("/patients/{patId}")
async def getPatSummary(patId: str):
    """
    Get patient summary with conflicts.
    
    Args:
        patId: Patient identifier.
    
    Returns:
        Patient summary with conflicts.
    """
    pat = db.getPatRec(patId)
    
    if pat is None:
        raise HTTPException(status_code=404, detail=f"Patient {patId} not found")
    
    unres = [
        c for c in pat.get('confs', [])
        if c.get('resoStatus') == UNRESOLVED
    ]
    
    confResp = [
        createConfResp(
            confType=c.get('confType'),
            severity=c.get('severity'),
            desc=c.get('desc'),
            resoStatus=c.get('resoStatus'),
            detectAt=c.get('detectAt'),
            id=c.get('id'),
        )
        for c in unres
    ]
    
    resp = createPatSummResp(
        patId=pat.get('patId'),
        clinId=pat.get('clinId'),
        lastUpdated=pat.get('updatAt'),
        snapCnt=len(pat.get('snaps', [])),
        unresolConfCnt=len(unres),
        confs=confResp,
    )
    
    return resp


@app.post("/conflicts/{patId}/{confIdx}/resolve")
async def resolveConf(patId: str, confIdx: int, resoReason: str = Query(..., description="Why resolved"), resolveBy: str = Query(..., description="User/system")):
    """
    Mark conflict as resolved.
    
    Args:
        patId: Patient identifier.
        confIdx: Index of conflict.
        resoReason: Reason for resolution.
        resolveBy: User or system that resolved.
    
    Returns:
        Success message.
    """
    pat = db.getPatRec(patId)
    
    if pat is None:
        raise HTTPException(status_code=404, detail=f"Patient {patId} not found")
    
    if confIdx < 0 or confIdx >= len(pat.get('confs', [])):
        raise HTTPException(status_code=400, detail="Invalid conflict index")
    
    db.resolveConf(patId, confIdx, resoReason, resolveBy)
    
    return {"status": "success", "msg": "Conflict resolved"}




@app.get("/health")
async def healthCheck():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "svc": "Medication Reconciliation Service",
        "ver": "1.0.0",
    }
