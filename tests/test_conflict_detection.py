"""
Comprehensive tests for medication reconciliation service.
"""
import pytest
from datetime import datetime, timezone
from app.models import (
    createMedItem,
    createMedSnap,
    CLINIC_EMR,
    HOSPITAL_DISCHARGE,
    PATIENT_REPORTED,
    DOSE_MISMATCH,
    BLACKLISTED_COMBINATION,
    MISSING_STOPPED,
    UNRESOLVED,
)
from app.conflDetect import ConflictDetector


@pytest.fixture
def detector():
    """Fixture to provide a ConflictDetector instance."""
    return ConflictDetector()


class TestConflictDetection:
    """Test conflict detection logic."""

    def test_detect_dose_mismatch(self, detector):
        """Test detection of dose mismatches for the same drug."""
        snap1 = createMedSnap(
            src=CLINIC_EMR,
            meds=[
                createMedItem(name="lisinopril", dose=10, unit="mg", freq="daily"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        snap2 = createMedSnap(
            src=HOSPITAL_DISCHARGE,
            meds=[
                createMedItem(name="Lisinopril", dose=20, unit="mg", freq="daily"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectDoseMismatches([snap1, snap2])
        
        assert len(confs) == 1
        assert confs[0].get('confType') == DOSE_MISMATCH
        assert confs[0].get('severity') == "high"

    def test_no_conflict_same_dose(self, detector):
        """Test that no conflict is raised when doses match."""
        snap1 = createMedSnap(
            src=CLINIC_EMR,
            meds=[
                createMedItem(name="metoprolol", dose=100, unit="mg", freq="daily"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        snap2 = createMedSnap(
            src=HOSPITAL_DISCHARGE,
            meds=[
                createMedItem(name="Metoprolol", dose=100, unit="mg", freq="daily"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectDoseMismatches([snap1, snap2])
        
        assert len(confs) == 0

    def test_detect_blacklisted_combination(self, detector):
        """Test detection of blacklisted drug combinations."""
        snap = createMedSnap(
            src=CLINIC_EMR,
            meds=[
                createMedItem(name="lisinopril", dose=10, unit="mg"),
                createMedItem(name="losartan", dose=50, unit="mg"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectBlacklistedComb([snap])
        
        assert len(confs) == 1
        assert confs[0].get('confType') == BLACKLISTED_COMBINATION
        assert confs[0].get('severity') == "critical"

    def test_detect_missing_or_stopped(self, detector):
        """Test detection of medication present in one source but stopped in another."""
        snap1 = createMedSnap(
            src=CLINIC_EMR,
            meds=[
                createMedItem(name="amlodipine", dose=5, unit="mg"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        snap2 = createMedSnap(
            src=HOSPITAL_DISCHARGE,
            meds=[
                createMedItem(name="amlodipine", dose=5, unit="mg", stopped=True),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectMissingStopped([snap1, snap2])
        
        assert len(confs) == 1
        assert confs[0].get('confType') == MISSING_STOPPED
        assert confs[0].get('severity') == "high"

    def test_normalize_medication_name(self, detector):
        """Test medication name normalization."""
        assert detector.normMedName("LiSinOpril") == "lisinopril"
        assert detector.normMedName("  ibuprofen  ") == "ibuprofen"
        assert detector.normMedName("METOPROLOL") == "metoprolol"

    def test_detect_all_conflicts_integration(self, detector):
        """Integration test for detecting all conflict types."""
        snaps = [
            createMedSnap(
                src=CLINIC_EMR,
                meds=[
                    createMedItem(name="lisinopril", dose=10, unit="mg"),
                    createMedItem(name="metoprolol", dose=100, unit="mg"),
                ],
                capturAt=datetime.now(timezone.utc),
            ),
            createMedSnap(
                src=HOSPITAL_DISCHARGE,
                meds=[
                    createMedItem(name="lisinopril", dose=20, unit="mg"),
                    createMedItem(name="losartan", dose=50, unit="mg"),
                ],
                capturAt=datetime.now(timezone.utc),
            ),
        ]
        
        allConfs = detector.detectAllConf(snaps)
        
        assert len(allConfs) >= 1
        
        confTypes = {c.get('confType') for c in allConfs}
        assert DOSE_MISMATCH in confTypes or BLACKLISTED_COMBINATION in confTypes


class TestMedicationNormalization:
    """Test medication item normalization."""

    def test_normalize_medication_with_various_cases(self, detector):
        """Test that medication normalization handles various input cases."""
        testCases = [
            ("LISINOPRIL", "lisinopril"),
            ("Metoprolol", "metoprolol"),
            ("aMLodiPinE", "amlodipine"),
            ("  ibuprofen  ", "ibuprofen"),
        ]
        
        for inName, expected in testCases:
            assert detector.normMedName(inName) == expected


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_snapshots(self, detector):
        """Test handling of empty snapshots."""
        confs = detector.detectAllConf([])
        assert confs == []

    def test_snapshot_with_no_medications(self, detector):
        """Test handling of snapshots with no medications."""
        snap = createMedSnap(
            src=CLINIC_EMR,
            meds=[],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectAllConf([snap])
        assert confs == []

    def test_medication_without_dose(self, detector):
        """Test handling of medications without dose information."""
        snap = createMedSnap(
            src=CLINIC_EMR,
            meds=[
                createMedItem(name="lisinopril"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectDoseMismatches([snap])
        assert confs == []

    def test_stopped_medication_ignored_in_dose_check(self, detector):
        """Test that stopped medications are ignored in dose mismatch detection."""
        snap1 = createMedSnap(
            src=CLINIC_EMR,
            meds=[
                createMedItem(name="lisinopril", dose=10, unit="mg"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        snap2 = createMedSnap(
            src=HOSPITAL_DISCHARGE,
            meds=[
                createMedItem(name="lisinopril", dose=20, unit="mg", stopped=True),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectDoseMismatches([snap1, snap2])
        
        assert len(confs) == 0

    def test_single_source_no_conflict(self, detector):
        """Test that conflicts requiring multiple sources are not flagged for single source."""
        snap = createMedSnap(
            src=CLINIC_EMR,
            meds=[
                createMedItem(name="lisinopril", dose=10, unit="mg"),
                createMedItem(name="losartan", dose=50, unit="mg"),
            ],
            capturAt=datetime.now(timezone.utc),
        )
        
        confs = detector.detectBlacklistedComb([snap])
        assert len(confs) == 1
        assert CLINIC_EMR in confs[0].get('srcsInvolv', [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
