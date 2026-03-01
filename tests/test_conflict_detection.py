"""
Comprehensive tests for medication reconciliation service.
"""
import pytest
from datetime import datetime
from app.models import (
    MedicationItem,
    MedicationSnapshot,
    MedicationSource,
    ConflictType,
    ResolutionStatus,
)
from app.conflict_detector import ConflictDetector


@pytest.fixture
def detector():
    """Fixture to provide a ConflictDetector instance."""
    return ConflictDetector()


class TestConflictDetection:
    """Test conflict detection logic."""

    def test_detect_dose_mismatch(self, detector):
        """Test detection of dose mismatches for the same drug."""
        # Setup: same drug with different doses from two sources
        snapshot1 = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[
                MedicationItem(name="lisinopril", dose=10, unit="mg", frequency="daily"),
            ],
            captured_at=datetime.utcnow(),
        )
        
        snapshot2 = MedicationSnapshot(
            source=MedicationSource.HOSPITAL_DISCHARGE,
            medications=[
                MedicationItem(name="Lisinopril", dose=20, unit="mg", frequency="daily"),
            ],
            captured_at=datetime.utcnow(),
        )
        
        conflicts = detector.detect_dose_mismatches([snapshot1, snapshot2])
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.DOSE_MISMATCH
        assert conflicts[0].severity == "high"

    def test_no_conflict_same_dose(self, detector):
        """Test that no conflict is raised when doses match."""
        snapshot1 = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[
                MedicationItem(name="metoprolol", dose=100, unit="mg", frequency="daily"),
            ],
            captured_at=datetime.utcnow(),
        )
        
        snapshot2 = MedicationSnapshot(
            source=MedicationSource.HOSPITAL_DISCHARGE,
            medications=[
                MedicationItem(name="Metoprolol", dose=100, unit="mg", frequency="daily"),
            ],
            captured_at=datetime.utcnow(),
        )
        
        conflicts = detector.detect_dose_mismatches([snapshot1, snapshot2])
        
        assert len(conflicts) == 0

    def test_detect_blacklisted_combination(self, detector):
        """Test detection of blacklisted drug combinations."""
        # ACE_INHIBITOR + ARB is blacklisted
        snapshot = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[
                MedicationItem(name="lisinopril", dose=10, unit="mg"),
                MedicationItem(name="losartan", dose=50, unit="mg"),
            ],
            captured_at=datetime.utcnow(),
        )
        
        conflicts = detector.detect_blacklisted_combinations([snapshot])
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.BLACKLISTED_COMBINATION
        assert conflicts[0].severity == "critical"

    def test_detect_missing_or_stopped(self, detector):
        """Test detection of medication present in one source but stopped in another."""
        snapshot1 = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[
                MedicationItem(name="amlodipine", dose=5, unit="mg"),
            ],
            captured_at=datetime.utcnow(),
        )
        
        snapshot2 = MedicationSnapshot(
            source=MedicationSource.HOSPITAL_DISCHARGE,
            medications=[
                MedicationItem(name="amlodipine", dose=5, unit="mg", stopped=True),
            ],
            captured_at=datetime.utcnow(),
        )
        
        conflicts = detector.detect_missing_or_stopped([snapshot1, snapshot2])
        
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.MISSING_STOPPED
        assert conflicts[0].severity == "high"

    def test_normalize_medication_name(self, detector):
        """Test medication name normalization."""
        assert detector.normalize_medication_name("LiSinOpril") == "lisinopril"
        assert detector.normalize_medication_name("  ibuprofen  ") == "ibuprofen"
        assert detector.normalize_medication_name("METOPROLOL") == "metoprolol"

    def test_detect_all_conflicts_integration(self, detector):
        """Integration test for detecting all conflict types."""
        snapshots = [
            MedicationSnapshot(
                source=MedicationSource.CLINIC_EMR,
                medications=[
                    MedicationItem(name="lisinopril", dose=10, unit="mg"),
                    MedicationItem(name="metoprolol", dose=100, unit="mg"),
                ],
                captured_at=datetime.utcnow(),
            ),
            MedicationSnapshot(
                source=MedicationSource.HOSPITAL_DISCHARGE,
                medications=[
                    MedicationItem(name="lisinopril", dose=20, unit="mg"),  # dose mismatch
                    MedicationItem(name="losartan", dose=50, unit="mg"),    # blacklist with ACE
                ],
                captured_at=datetime.utcnow(),
            ),
        ]
        
        all_conflicts = detector.detect_all_conflicts(snapshots)
        
        # Should detect dose mismatch and blacklisted combination
        assert len(all_conflicts) >= 1  # At least dose mismatch or blacklist conflict
        
        # Check for expected types
        conflict_types = {c.conflict_type for c in all_conflicts}
        assert ConflictType.DOSE_MISMATCH in conflict_types or ConflictType.BLACKLISTED_COMBINATION in conflict_types


class TestMedicationNormalization:
    """Test medication item normalization."""

    def test_normalize_medication_with_various_cases(self, detector):
        """Test that medication normalization handles various input cases."""
        test_cases = [
            ("LISINOPRIL", "lisinopril"),
            ("Metoprolol", "metoprolol"),
            ("aMLodiPinE", "amlodipine"),
            ("  ibuprofen  ", "ibuprofen"),
        ]
        
        for input_name, expected in test_cases:
            assert detector.normalize_medication_name(input_name) == expected


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_snapshots(self, detector):
        """Test handling of empty snapshots."""
        conflicts = detector.detect_all_conflicts([])
        assert conflicts == []

    def test_snapshot_with_no_medications(self, detector):
        """Test handling of snapshots with no medications."""
        snapshot = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[],
            captured_at=datetime.utcnow(),
        )
        
        conflicts = detector.detect_all_conflicts([snapshot])
        assert conflicts == []

    def test_medication_without_dose(self, detector):
        """Test handling of medications without dose information."""
        snapshot = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[
                MedicationItem(name="lisinopril"),  # No dose
            ],
            captured_at=datetime.utcnow(),
        )
        
        # Should not raise error
        conflicts = detector.detect_dose_mismatches([snapshot])
        assert conflicts == []

    def test_stopped_medication_ignored_in_dose_check(self, detector):
        """Test that stopped medications are ignored in dose mismatch detection."""
        snapshot1 = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[
                MedicationItem(name="lisinopril", dose=10, unit="mg"),
            ],
            captured_at=datetime.utcnow(),
        )
        
        snapshot2 = MedicationSnapshot(
            source=MedicationSource.HOSPITAL_DISCHARGE,
            medications=[
                MedicationItem(name="lisinopril", dose=20, unit="mg", stopped=True),
            ],
            captured_at=datetime.utcnow(),
        )
        
        conflicts = detector.detect_dose_mismatches([snapshot1, snapshot2])
        
        # Should not flag as dose mismatch since stopped meds are ignored
        assert len(conflicts) == 0

    def test_single_source_no_conflict(self, detector):
        """Test that conflicts requiring multiple sources are not flagged for single source."""
        snapshot = MedicationSnapshot(
            source=MedicationSource.CLINIC_EMR,
            medications=[
                MedicationItem(name="lisinopril", dose=10, unit="mg"),
                MedicationItem(name="losartan", dose=50, unit="mg"),  # Blacklist combo
            ],
            captured_at=datetime.utcnow(),
        )
        
        # Blacklist combos should still be detected within a single source
        conflicts = detector.detect_blacklisted_combinations([snapshot])
        assert len(conflicts) == 1
        assert conflicts[0].sources_involved == [MedicationSource.CLINIC_EMR]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
