"""
Core conflict detection logic for medication reconciliation.
"""
import json
from datetime import datetime
from typing import List, Dict, Set, Tuple
from pathlib import Path
from .models import (
    MedicationItem,
    MedicationSnapshot,
    MedicationConflict,
    ConflictType,
    MedicationSource,
    ResolutionStatus,
)


class ConflictDetector:
    """Detects medication conflicts across sources."""

    def __init__(self, rules_path: str = None):
        """
        Initialize the detector with conflict rules.
        
        Args:
            rules_path: Path to conflict_rules.json. If None, uses default location.
        """
        if rules_path is None:
            # Default to data/conflict_rules.json relative to this file
            rules_path = Path(__file__).parent.parent / "data" / "conflict_rules.json"
        
        with open(rules_path, "r") as f:
            self.rules = json.load(f)
        
        # Build reverse mapping: drug name -> class
        self.drug_to_class: Dict[str, str] = {}
        for drug_class, drugs in self.rules["drug_classes"].items():
            for drug in drugs:
                self.drug_to_class[drug.lower()] = drug_class

    def normalize_medication_name(self, name: str) -> str:
        """Normalize medication name for comparison."""
        return name.lower().strip()

    def normalize_unit(self, unit: str) -> str:
        """Normalize unit for comparison."""
        if not unit:
            return ""
        return unit.lower().strip()

    def extract_snapshots_by_source(
        self, snapshots: List[MedicationSnapshot]
    ) -> Dict[MedicationSource, List[MedicationItem]]:
        """Organize medications by source."""
        by_source = {}
        for snapshot in snapshots:
            if snapshot.source not in by_source:
                by_source[snapshot.source] = []
            by_source[snapshot.source].extend(snapshot.medications)
        return by_source

    def detect_dose_mismatches(
        self, snapshots: List[MedicationSnapshot]
    ) -> List[MedicationConflict]:
        """Detect dose differences for the same drug across sources."""
        conflicts = []
        by_source = self.extract_snapshots_by_source(snapshots)
        
        # Map normalized names to all occurrences
        drug_records: Dict[str, List[Tuple[str, MedicationItem, MedicationSource]]] = {}
        
        for source, meds in by_source.items():
            for med in meds:
                if med.stopped:
                    continue  # Skip stopped medications for dose checks
                
                norm_name = self.normalize_medication_name(med.name)
                if norm_name not in drug_records:
                    drug_records[norm_name] = []
                drug_records[norm_name].append((med.name, med, source))
        
        # Check each drug across sources
        for norm_name, records in drug_records.items():
            sources_set = {r[2] for r in records}
            
            # Only flag if drug appears in multiple sources
            if len(sources_set) < 2:
                continue
            
            # Check dose consistency
            doses = [(r[1].dose, r[1].unit, r[2]) for r in records if r[1].dose is not None]
            
            if len(doses) > 1:
                # Check if all doses and units match
                unique_doses = set((d[0], self.normalize_unit(d[1])) for d in doses)
                
                if len(unique_doses) > 1:
                    sources_involved = [d[2] for d in doses]
                    conflict = MedicationConflict(
                        conflict_type=ConflictType.DOSE_MISMATCH,
                        sources_involved=sources_involved,
                        drug_names=[med.name for _, med, _ in records if med.dose is not None],
                        description=f"Dose mismatch for {norm_name}: "
                                   f"{', '.join(str(d[0]) + d[1] for d in doses)}",
                        severity="high",
                        detected_at=datetime.utcnow(),
                        resolution_status=ResolutionStatus.UNRESOLVED,
                    )
                    conflicts.append(conflict)
        
        return conflicts

    def detect_blacklisted_combinations(
        self, snapshots: List[MedicationSnapshot]
    ) -> List[MedicationConflict]:
        """Detect blacklisted drug combinations within a single source or across sources."""
        conflicts = []
        by_source = self.extract_snapshots_by_source(snapshots)
        
        # Normalize all medications
        normalized_by_source = {}
        for source, meds in by_source.items():
            normalized = [
                (self.normalize_medication_name(m.name), m)
                for m in meds if not m.stopped
            ]
            normalized_by_source[source] = normalized
        
        # Check each source for blacklisted combinations
        for source, normalized_meds in normalized_by_source.items():
            drug_classes_present: Dict[str, List[str]] = {}
            
            for norm_name, med in normalized_meds:
                if norm_name in self.drug_to_class:
                    drug_class = self.drug_to_class[norm_name]
                    if drug_class not in drug_classes_present:
                        drug_classes_present[drug_class] = []
                    drug_classes_present[drug_class].append(med.name)
            
            # Check blacklist rules
            for rule in self.rules["blacklisted_combinations"]:
                classes_in_rule = set(rule["drugs"])
                classes_present = set(drug_classes_present.keys())
                
                if classes_in_rule.issubset(classes_present):
                    # Found a blacklisted combination
                    drug_names = []
                    for drug_class in classes_in_rule:
                        drug_names.extend(drug_classes_present[drug_class])
                    
                    conflict = MedicationConflict(
                        conflict_type=ConflictType.BLACKLISTED_COMBINATION,
                        sources_involved=[source],
                        drug_names=drug_names,
                        description=f"Blacklisted combination detected in {source.value}: "
                                   f"{', '.join(drug_names)}. Reason: {rule['reason']}",
                        severity="critical",
                        detected_at=datetime.utcnow(),
                        resolution_status=ResolutionStatus.UNRESOLVED,
                    )
                    conflicts.append(conflict)
        
        return conflicts

    def detect_missing_or_stopped(
        self, snapshots: List[MedicationSnapshot]
    ) -> List[MedicationConflict]:
        """Detect when a medication is present in one source but stopped in another."""
        conflicts = []
        by_source = self.extract_snapshots_by_source(snapshots)
        
        # Map drugs to sources where they're active/stopped
        drug_status: Dict[str, Dict[str, bool]] = {}  # drug_name -> {source -> is_active}
        
        for source, meds in by_source.items():
            for med in meds:
                norm_name = self.normalize_medication_name(med.name)
                if norm_name not in drug_status:
                    drug_status[norm_name] = {}
                drug_status[norm_name][source.value] = not med.stopped
        
        # Check for conflicts
        for norm_name, statuses in drug_status.items():
            if len(statuses) < 2:
                continue  # Only flag if drug appears in multiple sources
            
            active_sources = [s for s, is_active in statuses.items() if is_active]
            stopped_sources = [s for s, is_active in statuses.items() if not is_active]
            
            if active_sources and stopped_sources:
                # Drug is active in some sources but stopped in others
                conflict = MedicationConflict(
                    conflict_type=ConflictType.MISSING_STOPPED,
                    sources_involved=[s for s in statuses.keys()],
                    drug_names=[norm_name],
                    description=f"Medication {norm_name} is active in {active_sources} "
                               f"but stopped in {stopped_sources}",
                    severity="high",
                    detected_at=datetime.utcnow(),
                    resolution_status=ResolutionStatus.UNRESOLVED,
                )
                conflicts.append(conflict)
        
        return conflicts

    def detect_all_conflicts(
        self, snapshots: List[MedicationSnapshot]
    ) -> List[MedicationConflict]:
        """Detect all types of conflicts."""
        conflicts = []
        conflicts.extend(self.detect_dose_mismatches(snapshots))
        conflicts.extend(self.detect_blacklisted_combinations(snapshots))
        conflicts.extend(self.detect_missing_or_stopped(snapshots))
        
        # Remove duplicates by description (simple dedup)
        unique_conflicts = []
        seen = set()
        for conflict in conflicts:
            desc_key = (conflict.conflict_type, tuple(sorted(conflict.drug_names)))
            if desc_key not in seen:
                seen.add(desc_key)
                unique_conflicts.append(conflict)
        
        return unique_conflicts
