"""
Plain Python models for medication reconciliation (no Pydantic/Enum/typing).
Uses dictionaries and string constants for validation.
"""
from datetime import datetime, timezone

CLINIC_EMR = "clinic_emr"
HOSPITAL_DISCHARGE = "hospital_discharge"
PATIENT_REPORTED = "patient_reported"

MEDICATION_SOURCES = {
    CLINIC_EMR,
    HOSPITAL_DISCHARGE,
    PATIENT_REPORTED,
}

DOSE_MISMATCH = "dose_mismatch"
BLACKLISTED_COMBINATION = "blacklisted_combination"
MISSING_STOPPED = "missing_stopped"
DIFFERENT_FORMULATION = "different_formulation"

CONFLICT_TYPES = {
    DOSE_MISMATCH,
    BLACKLISTED_COMBINATION,
    MISSING_STOPPED,
    DIFFERENT_FORMULATION,
}

UNRESOLVED = "unresolved"
RESOLVED = "resolved"
ACKNOWLEDGED = "acknowledged"

RESOLUTION_STATUSES = {
    UNRESOLVED,
    RESOLVED,
    ACKNOWLEDGED,
}



def createMedItem(name, dose=None, unit=None, freq=None, route=None, stopped=False, notes=None):
    """Create medication item dict."""
    return {
        "name": name,
        "dose": dose,
        "unit": unit,
        "freq": freq,
        "route": route,
        "stopped": stopped,
        "notes": notes,
    }


def createMedSnap(src, meds, capturAt=None, clinId=None, notes=None):
    """Create medication snapshot dict."""
    if capturAt is None:
        capturAt = datetime.now(timezone.utc)
    if isinstance(capturAt, str):
        capturAt = datetime.fromisoformat(capturAt)
    
    return {
        "src": src,
        "meds": meds if isinstance(meds, list) else list(meds),
        "capturAt": capturAt,
        "clinId": clinId,
        "notes": notes,
    }


def createMedConf(confType, srcsInvolv, drugNames, desc, 
                  severity="medium", detectAt=None, resoStatus=None,
                  resoReason=None, resolveBy=None, resolveAt=None, 
                  metadata=None):
    """Create medication conflict dict."""
    if detectAt is None:
        detectAt = datetime.now(timezone.utc)
    if isinstance(detectAt, str):
        detectAt = datetime.fromisoformat(detectAt)
    
    if resoStatus is None:
        resoStatus = RESOLUTION_STATUS_UNRESOLVED
    
    if isinstance(resolveAt, str):
        resolveAt = datetime.fromisoformat(resolveAt)
    
    if metadata is None:
        metadata = {}
    
    return {
        "confType": confType,
        "srcsInvolv": srcsInvolv,
        "drugNames": drugNames,
        "desc": desc,
        "severity": severity,
        "detectAt": detectAt,
        "resoStatus": resoStatus,
        "resoReason": resoReason,
        "resolveBy": resolveBy,
        "resolveAt": resolveAt,
        "metadata": metadata,
    }


def createPatMedRec(patId, clinId, snaps=None, confs=None, 
                    creatAt=None, updatAt=None):
    """Create patient medication record dict."""
    if creatAt is None:
        creatAt = datetime.now(timezone.utc)
    if isinstance(creatAt, str):
        creatAt = datetime.fromisoformat(creatAt)
    
    if updatAt is None:
        updatAt = datetime.now(timezone.utc)
    if isinstance(updatAt, str):
        updatAt = datetime.fromisoformat(updatAt)
    
    return {
        "patId": patId,
        "clinId": clinId,
        "snaps": snaps if snaps is not None else [],
        "confs": confs if confs is not None else [],
        "creatAt": creatAt,
        "updatAt": updatAt,
    }


def createIngestReq(patId, clinId, src, meds, notes=None):
    """Create ingestion request dict."""
    return {
        "patId": patId,
        "clinId": clinId,
        "src": src,
        "meds": meds,
        "notes": notes,
    }


def createConfResp(confType, severity, desc, resoStatus, detectAt, id=None):
    """Create conflict response dict."""
    return {
        "id": id,
        "confType": confType,
        "severity": severity,
        "desc": desc,
        "resoStatus": resoStatus,
        "detectAt": detectAt,
    }


def createPatSummResp(patId, clinId, lastUpdated, snapCnt, 
                      unresolConfCnt, confs):
    """Create patient summary response dict."""
    return {
        "patId": patId,
        "clinId": clinId,
        "lastUpdated": lastUpdated,
        "snapCnt": snapCnt,
        "unresolConfCnt": unresolConfCnt,
        "confs": confs,
    }


def createRepQuery(clinId=None, startDt=None, endDt=None, minConf=1):
    """Create reporting query dict."""
    return {
        "clinId": clinId,
        "startDt": startDt,
        "endDt": endDt,
        "minConf": minConf,
    }
