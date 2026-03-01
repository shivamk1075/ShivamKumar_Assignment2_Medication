"""
Core conflict detection logic for medication reconciliation.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from .models import (
    DOSE_MISMATCH,
    BLACKLISTED_COMBINATION,
    MISSING_STOPPED,
    UNRESOLVED,
    CLINIC_EMR,
    HOSPITAL_DISCHARGE,
    PATIENT_REPORTED,
    createMedConf,
)


class ConflictDetector:
    """Detects medication conflicts across sources."""

    def __init__(self, rules_path=None):
        """
        Initialize the detector with conflict rules.
        
        Args:
            rules_path: Path to conflict_rules.json. If None, uses default location.
        """
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "data" / "conflict_rules.json"
        
        with open(rules_path, "r") as f:
            self.rules = json.load(f)
        
        self.drugToClass = {}
        for drugClass, drugs in self.rules["drug_classes"].items():
            for drug in drugs:
                self.drugToClass[drug.lower()] = drugClass

    def normMedName(self, name):
        """Normalize medication name for comparison."""
        return name.lower().strip()

    def normUnit(self, unit):
        """Normalize unit for comparison."""
        if not unit:
            return ""
        return unit.lower().strip()

    def extractSnapsBySrc(self, snaps):
        """Organize medications by source (dict)."""
        bySrc = {}
        for snap in snaps:
            src = snap.get('src')
            if src not in bySrc:
                bySrc[src] = []
            bySrc[src].extend(snap.get('meds', []))
        return bySrc

    def detectDoseMismatches(self, snaps):
        """Detect dose differences for the same drug across sources (works with dicts)."""
        confs = []
        bySrc = self.extractSnapsBySrc(snaps)
        
        drugRecords = {}
        
        for src, meds in bySrc.items():
            for med in meds:
                if med.get('stopped'):
                    continue
                
                normName = self.normMedName(med.get('name', ''))
                if normName not in drugRecords:
                    drugRecords[normName] = []
                drugRecords[normName].append((med.get('name'), med, src))
        
        for normName, records in drugRecords.items():
            srcSet = {r[2] for r in records}
            
            if len(srcSet) < 2:
                continue
            
            doses = [(r[1].get('dose'), r[1].get('unit'), r[2]) for r in records if r[1].get('dose') is not None]
            
            if len(doses) > 1:
                uniqDoses = set((d[0], self.normUnit(d[1])) for d in doses)
                
                if len(uniqDoses) > 1:
                    srcsInvolved = [d[2] for d in doses]
                    conf = createMedConf(
                        confType=DOSE_MISMATCH,
                        srcsInvolv=srcsInvolved,
                        drugNames=[rec[0] for rec in records if rec[1].get('dose') is not None],
                        desc=f"Dose mismatch for {normName}: "
                                   f"{', '.join(str(d[0]) + str(d[1]) for d in doses)}",
                        severity="high",
                        detectAt=datetime.now(timezone.utc),
                        resoStatus=UNRESOLVED,
                    )
                    confs.append(conf)
        
        return confs

    def detectBlacklistedComb(self, snaps):
        """Detect blacklisted drug combinations within a single source or across sources (works with dicts)."""
        confs = []
        bySrc = self.extractSnapsBySrc(snaps)
        
        normBySrc = {}
        for src, meds in bySrc.items():
            norm = [
                (self.normMedName(m.get('name', '')), m)
                for m in meds if not m.get('stopped')
            ]
            normBySrc[src] = norm
        
        for src, normMeds in normBySrc.items():
            drugClassesPresent = {}
            
            for normName, med in normMeds:
                if normName in self.drugToClass:
                    drugClass = self.drugToClass[normName]
                    if drugClass not in drugClassesPresent:
                        drugClassesPresent[drugClass] = []
                    drugClassesPresent[drugClass].append(med.get('name'))
            
            for rule in self.rules["blacklisted_combinations"]:
                classesInRule = set(rule["drugs"])
                classesPresent = set(drugClassesPresent.keys())
                
                if classesInRule.issubset(classesPresent):
                    drugNames = []
                    for drugClass in classesInRule:
                        drugNames.extend(drugClassesPresent[drugClass])
                    
                    conf = createMedConf(
                        confType=BLACKLISTED_COMBINATION,
                        srcsInvolv=[src],
                        drugNames=drugNames,
                        desc=f"Blacklisted combination detected in {src}: "
                                   f"{', '.join(drugNames)}. Reason: {rule['reason']}",
                        severity="critical",
                        detectAt=datetime.now(timezone.utc),
                        resoStatus=UNRESOLVED,
                    )
                    confs.append(conf)
        
        return confs

    def detectMissingStopped(self, snaps):
        """Detect when a medication is present in one source but stopped in another (works with dicts)."""
        confs = []
        bySrc = self.extractSnapsBySrc(snaps)
        
        drugStatus = {}
        
        for src, meds in bySrc.items():
            for med in meds:
                normName = self.normMedName(med.get('name', ''))
                if normName not in drugStatus:
                    drugStatus[normName] = {}
                drugStatus[normName][src] = not med.get('stopped', False)
        
        for normName, statuses in drugStatus.items():
            if len(statuses) < 2:
                continue
            
            activeSrcs = [s for s, isActive in statuses.items() if isActive]
            stoppedSrcs = [s for s, isActive in statuses.items() if not isActive]
            
            if activeSrcs and stoppedSrcs:
                conf = createMedConf(
                    confType=MISSING_STOPPED,
                    srcsInvolv=list(statuses.keys()),
                    drugNames=[normName],
                    desc=f"Medication {normName} is active in {activeSrcs} "
                               f"but stopped in {stoppedSrcs}",
                    severity="high",
                    detectAt=datetime.now(timezone.utc),
                    resoStatus=UNRESOLVED,
                )
                confs.append(conf)
        
        return confs

    def detectAllConf(self, snaps):
        """Detect all types of conflicts (works with dicts)."""
        confs = []
        confs.extend(self.detectDoseMismatches(snaps))
        confs.extend(self.detectBlacklistedComb(snaps))
        confs.extend(self.detectMissingStopped(snaps))
        
        uniqConfs = []
        seen = set()
        for conf in confs:
            descKey = (conf.get('confType'), tuple(sorted(conf.get('drugNames', []))))
            if descKey not in seen:
                seen.add(descKey)
                uniqConfs.append(conf)
        
        return uniqConfs
