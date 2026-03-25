"""
Test suite for HydroModelSpec Validator.

Run: python -m pytest tests/ -v
Or:  python tests/test_validator.py
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validator.validate import (
    validate, validate_dict, ValidationReport, Severity, RuleModule
)


EXAMPLES_DIR = str(Path(__file__).parent.parent / "examples")
SCHEMAS_DIR = str(Path(__file__).parent.parent / "schemas")


class TestValidArtifacts(unittest.TestCase):
    """Test that valid artifacts pass validation."""
    
    def test_valid_lstm_streamflow(self):
        report = validate(
            os.path.join(EXAMPLES_DIR, "valid_lstm_streamflow.json"),
            schema_dir=SCHEMAS_DIR
        )
        self.assertTrue(report.is_valid, f"Errors: {[r.message for r in report.errors]}")
    
    def test_valid_cnn_waterlevel(self):
        report = validate(
            os.path.join(EXAMPLES_DIR, "valid_cnn_waterlevel.json"),
            schema_dir=SCHEMAS_DIR
        )
        self.assertTrue(report.is_valid, f"Errors: {[r.message for r in report.errors]}")
    
    def test_minimal_valid(self):
        report = validate(
            os.path.join(EXAMPLES_DIR, "minimal_valid.json"),
            schema_dir=SCHEMAS_DIR
        )
        self.assertTrue(report.is_valid, f"Errors: {[r.message for r in report.errors]}")


class TestInvalidArtifacts(unittest.TestCase):
    """Test that invalid artifacts are correctly flagged."""
    
    def test_invalid_artifact_detected(self):
        report = validate(
            os.path.join(EXAMPLES_DIR, "invalid_artifact.json"),
            schema_dir=SCHEMAS_DIR
        )
        self.assertFalse(report.is_valid)
        self.assertGreater(len(report.errors), 0)


class TestRuleModule(unittest.TestCase):
    """Test individual rule checks."""
    
    def setUp(self):
        self.rules = RuleModule()
    
    def test_id_prefix_warning(self):
        report = ValidationReport()
        artifact = {"id": "no-prefix-123", "specVersion": "hms-core@1.0"}
        self.rules._check_id_format(artifact, report)
        warnings = [r for r in report.results if r.severity == Severity.WARNING]
        self.assertEqual(len(warnings), 1)
        self.assertIn("hms-", warnings[0].message)
    
    def test_valid_id_no_warning(self):
        report = ValidationReport()
        artifact = {"id": "hms-valid-123"}
        self.rules._check_id_format(artifact, report)
        warnings = [r for r in report.results if r.severity == Severity.WARNING]
        self.assertEqual(len(warnings), 0)
    
    def test_nse_exceeds_max(self):
        report = ValidationReport()
        artifact = {"evaluation": {"metrics": {"nse": 1.5}}}
        self.rules._check_metrics_range(artifact, report)
        errors = [r for r in report.results if r.severity == Severity.ERROR]
        self.assertEqual(len(errors), 1)
        self.assertIn("NSE", errors[0].message)
    
    def test_negative_rmse(self):
        report = ValidationReport()
        artifact = {"evaluation": {"metrics": {"rmse": -50}}}
        self.rules._check_metrics_range(artifact, report)
        errors = [r for r in report.results if r.severity == Severity.ERROR]
        self.assertEqual(len(errors), 1)
        self.assertIn("RMSE", errors[0].message)
    
    def test_privacy_consistency_violation(self):
        report = ValidationReport()
        artifact = {"privacy": {
            "trainedLocally": True,
            "dataTransmitted": True,
            "attestationMethod": "self_declared",
            "attestedAt": "2025-01-01T00:00:00Z"
        }}
        self.rules._check_privacy_consistency(artifact, report)
        errors = [r for r in report.results if r.severity == Severity.ERROR]
        self.assertEqual(len(errors), 1)
        self.assertIn("inconsistency", errors[0].message.lower())
    
    def test_valid_privacy_no_error(self):
        report = ValidationReport()
        artifact = {"privacy": {
            "trainedLocally": True,
            "dataTransmitted": False,
            "attestationMethod": "platform_verified",
            "platformId": "hydrolabai-v1.0",
            "attestedAt": "2025-01-01T00:00:00Z"
        }}
        self.rules._check_privacy_consistency(artifact, report)
        errors = [r for r in report.results if r.severity == Severity.ERROR]
        self.assertEqual(len(errors), 0)
    
    def test_data_split_sum_warning(self):
        report = ValidationReport()
        artifact = {"training": {"dataSplit": {
            "train": 0.5, "val": 0.2, "test": 0.1, "method": "chronological"
        }}}
        self.rules._check_data_split_sum(artifact, report)
        warnings = [r for r in report.results if r.severity == Severity.WARNING]
        self.assertEqual(len(warnings), 1)
    
    def test_invalid_hash_format(self):
        report = ValidationReport()
        artifact = {
            "training": {"datasetHash": "not-a-hash"},
            "weights": {},
        }
        self.rules._check_hash_formats(artifact, report)
        errors = [r for r in report.results if r.severity == Severity.ERROR]
        self.assertEqual(len(errors), 1)
    
    def test_timestamp_ordering(self):
        report = ValidationReport()
        artifact = {
            "createdAt": "2025-03-01T00:00:00Z",
            "updatedAt": "2025-02-01T00:00:00Z",
            "training": {}
        }
        self.rules._check_timestamps(artifact, report)
        errors = [r for r in report.results if r.severity == Severity.ERROR]
        self.assertEqual(len(errors), 1)
        self.assertIn("updatedAt", errors[0].message)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_nonexistent_file(self):
        report = validate("/nonexistent/path.json")
        self.assertFalse(report.is_valid)
        self.assertIn("LOAD-002", report.errors[0].rule_code)
    
    def test_invalid_json(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{not valid json")
            f.flush()
            report = validate(f.name)
            self.assertFalse(report.is_valid)
            self.assertIn("LOAD-001", report.errors[0].rule_code)
            os.unlink(f.name)
    
    def test_dict_validation(self):
        artifact = {
            "id": "hms-test-001",
            "specVersion": "hms-core@1.0",
            "name": "Test",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
            "architecture": {"type": "LSTM"},
            "training": {
                "optimizer": "Adam", "learningRate": 0.001,
                "epochs": 1, "lossFunction": "MSE",
                "dataSplit": {"train": 0.7, "val": 0.15, "test": 0.15, "method": "chronological"}
            },
            "inputSchema": {"shape": ["N", 10, 1], "dtype": "float32"},
            "outputSchema": {"shape": ["N", 1], "dtype": "float32"},
            "evaluation": {"metrics": {"rmse": 100.0}, "splitUsed": "test"},
            "weights": {"format": "numpy_npz", "uri": "weights/test.npz"},
            "metadata": {"license": "MIT"}
        }
        report = validate_dict(artifact, schema_dir=SCHEMAS_DIR)
        self.assertTrue(report.is_valid, f"Errors: {[r.message for r in report.errors]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
