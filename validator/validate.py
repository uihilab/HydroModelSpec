"""
HydroModelSpec Validator

Enforcement-grade validation for HydroModelSpec-compliant model artifacts.
Three-layer architecture:
  1. Schema Validator  - JSON Schema Draft 2020-12 structural conformance
  2. Data Validator    - Instance validation against core/profile schemas
  3. Rule Module       - Domain-specific logical and semantic constraints

Usage:
    CLI:    python -m validator artifact.json
    Python: from validator import validate; results = validate("artifact.json")
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    import jsonschema
    from jsonschema import Draft202012Validator, RefResolver
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# =============================================================================
# VALIDATION RESULT TYPES
# =============================================================================

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Single validation finding."""
    rule_code: str
    severity: Severity
    message: str
    json_path: str = ""
    
    def to_dict(self) -> dict:
        return {
            "rule_code": self.rule_code,
            "severity": self.severity.value,
            "message": self.message,
            "json_path": self.json_path,
        }


@dataclass
class ValidationReport:
    """Complete validation report for an artifact."""
    artifact_id: str = ""
    spec_version: str = ""
    is_valid: bool = True
    results: List[ValidationResult] = field(default_factory=list)
    
    def add(self, result: ValidationResult):
        self.results.append(result)
        if result.severity == Severity.ERROR:
            self.is_valid = False
    
    @property
    def errors(self) -> List[ValidationResult]:
        return [r for r in self.results if r.severity == Severity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationResult]:
        return [r for r in self.results if r.severity == Severity.WARNING]
    
    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "spec_version": self.spec_version,
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "results": [r.to_dict() for r in self.results],
        }
    
    def summary(self) -> str:
        status = "PASS" if self.is_valid else "FAIL"
        return (
            f"[{status}] {self.artifact_id} ({self.spec_version}) "
            f"- {len(self.errors)} errors, {len(self.warnings)} warnings"
        )


# =============================================================================
# SCHEMA VALIDATOR (Layer 1)
# =============================================================================

class SchemaValidator:
    """Validates JSON Schema definitions against the meta-schema."""
    
    def validate_schema(self, schema: dict, report: ValidationReport):
        if not HAS_JSONSCHEMA:
            report.add(ValidationResult(
                "SV-001", Severity.ERROR,
                "jsonschema library not installed. Run: pip install jsonschema"
            ))
            return
        
        try:
            Draft202012Validator.check_schema(schema)
            report.add(ValidationResult(
                "SV-100", Severity.INFO,
                "Schema is valid against JSON Schema Draft 2020-12."
            ))
        except jsonschema.SchemaError as e:
            report.add(ValidationResult(
                "SV-002", Severity.ERROR,
                f"Schema validation error: {e.message}",
                json_path=str(list(e.absolute_path))
            ))


# =============================================================================
# DATA VALIDATOR (Layer 2)
# =============================================================================

class DataValidator:
    """Validates model artifact instances against HydroModelSpec schemas."""
    
    def __init__(self, schema_dir: Optional[str] = None):
        self.schema_dir = schema_dir or str(
            Path(__file__).parent.parent / "schemas"
        )
    
    def _load_core_schema(self) -> dict:
        schema_path = os.path.join(self.schema_dir, "core", "core.schema.json")
        with open(schema_path, "r") as f:
            return json.load(f)
    
    def validate_instance(self, artifact: dict, report: ValidationReport):
        if not HAS_JSONSCHEMA:
            report.add(ValidationResult(
                "DV-001", Severity.ERROR,
                "jsonschema library not installed."
            ))
            return
        
        try:
            schema = self._load_core_schema()
        except FileNotFoundError:
            report.add(ValidationResult(
                "DV-002", Severity.ERROR,
                f"Core schema not found at {self.schema_dir}/core/core.schema.json"
            ))
            return
        
        try:
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(artifact))
            
            if not errors:
                report.add(ValidationResult(
                    "DV-100", Severity.INFO,
                    "Artifact conforms to HydroModelSpec Core Schema."
                ))
            else:
                for error in errors:
                    path = ".".join(str(p) for p in error.absolute_path)
                    report.add(ValidationResult(
                        "DV-003", Severity.ERROR,
                        f"Schema violation: {error.message}",
                        json_path=path or "(root)"
                    ))
        except Exception as e:
            report.add(ValidationResult(
                "DV-004", Severity.ERROR,
                f"Validation engine error: {str(e)}"
            ))


# =============================================================================
# RULE MODULE (Layer 3) - Domain-Specific Constraints
# =============================================================================

class RuleModule:
    """Enforces HydroModelSpec-specific logical and semantic constraints."""
    
    def validate_rules(self, artifact: dict, report: ValidationReport):
        self._check_id_format(artifact, report)
        self._check_spec_version(artifact, report)
        self._check_timestamps(artifact, report)
        self._check_metrics_range(artifact, report)
        self._check_privacy_consistency(artifact, report)
        self._check_hash_formats(artifact, report)
        self._check_data_split_sum(artifact, report)
        self._check_training_eval_consistency(artifact, report)
    
    def _check_id_format(self, artifact: dict, report: ValidationReport):
        model_id = artifact.get("id", "")
        if not model_id.startswith("hms-"):
            report.add(ValidationResult(
                "RM-001", Severity.WARNING,
                f"Model ID '{model_id}' should start with 'hms-' prefix.",
                json_path="id"
            ))
    
    def _check_spec_version(self, artifact: dict, report: ValidationReport):
        version = artifact.get("specVersion", "")
        if not version.startswith("hms-"):
            report.add(ValidationResult(
                "RM-002", Severity.ERROR,
                f"specVersion '{version}' must start with 'hms-' namespace.",
                json_path="specVersion"
            ))
    
    def _check_timestamps(self, artifact: dict, report: ValidationReport):
        created = artifact.get("createdAt", "")
        updated = artifact.get("updatedAt", "")
        if created and updated and updated < created:
            report.add(ValidationResult(
                "RM-003", Severity.ERROR,
                "updatedAt cannot be earlier than createdAt.",
                json_path="updatedAt"
            ))
        
        training = artifact.get("training", {})
        started = training.get("startedAt", "")
        completed = training.get("completedAt", "")
        if started and completed and completed < started:
            report.add(ValidationResult(
                "RM-004", Severity.ERROR,
                "training.completedAt cannot be earlier than training.startedAt.",
                json_path="training.completedAt"
            ))
    
    def _check_metrics_range(self, artifact: dict, report: ValidationReport):
        metrics = artifact.get("evaluation", {}).get("metrics", {})
        
        if "nse" in metrics and metrics["nse"] > 1.0:
            report.add(ValidationResult(
                "RM-010", Severity.ERROR,
                f"NSE value {metrics['nse']} exceeds theoretical maximum of 1.0.",
                json_path="evaluation.metrics.nse"
            ))
        
        if "rmse" in metrics and metrics["rmse"] < 0:
            report.add(ValidationResult(
                "RM-011", Severity.ERROR,
                f"RMSE value {metrics['rmse']} cannot be negative.",
                json_path="evaluation.metrics.rmse"
            ))
        
        if "kge" in metrics and metrics["kge"] > 1.0:
            report.add(ValidationResult(
                "RM-012", Severity.ERROR,
                f"KGE value {metrics['kge']} exceeds theoretical maximum of 1.0.",
                json_path="evaluation.metrics.kge"
            ))
        
        for m in ["precision", "recall", "f1", "csi"]:
            if m in metrics and not (0 <= metrics[m] <= 1):
                report.add(ValidationResult(
                    "RM-013", Severity.ERROR,
                    f"{m} value {metrics[m]} must be between 0 and 1.",
                    json_path=f"evaluation.metrics.{m}"
                ))
    
    def _check_privacy_consistency(self, artifact: dict, report: ValidationReport):
        privacy = artifact.get("privacy")
        if not privacy:
            return
        
        trained_locally = privacy.get("trainedLocally", False)
        data_transmitted = privacy.get("dataTransmitted", True)
        
        if trained_locally and data_transmitted:
            report.add(ValidationResult(
                "RM-020", Severity.ERROR,
                "Privacy inconsistency: trainedLocally=true requires dataTransmitted=false.",
                json_path="privacy"
            ))
        
        method = privacy.get("attestationMethod", "")
        if method == "platform_verified" and not privacy.get("platformId"):
            report.add(ValidationResult(
                "RM-021", Severity.WARNING,
                "platform_verified attestation should include platformId.",
                json_path="privacy.platformId"
            ))
    
    def _check_hash_formats(self, artifact: dict, report: ValidationReport):
        import re
        hash_pattern = re.compile(r"^sha256:[a-f0-9]{64}$")
        
        paths_to_check = [
            ("training.datasetHash", artifact.get("training", {}).get("datasetHash")),
            ("privacy.datasetHash", (artifact.get("privacy") or {}).get("datasetHash")),
            ("privacy.weightsHash", (artifact.get("privacy") or {}).get("weightsHash")),
            ("weights.hash", artifact.get("weights", {}).get("hash")),
        ]
        
        for path, value in paths_to_check:
            if value and not hash_pattern.match(value):
                report.add(ValidationResult(
                    "RM-030", Severity.ERROR,
                    f"Invalid hash format at {path}. Expected 'sha256:<64 hex chars>'.",
                    json_path=path
                ))
    
    def _check_data_split_sum(self, artifact: dict, report: ValidationReport):
        split = artifact.get("training", {}).get("dataSplit", {})
        if all(k in split for k in ["train", "val", "test"]):
            total = split["train"] + split["val"] + split["test"]
            if abs(total - 1.0) > 0.01:
                report.add(ValidationResult(
                    "RM-040", Severity.WARNING,
                    f"Data split ratios sum to {total:.3f}, expected ~1.0.",
                    json_path="training.dataSplit"
                ))
    
    def _check_training_eval_consistency(self, artifact: dict, report: ValidationReport):
        training = artifact.get("training", {})
        evaluation = artifact.get("evaluation", {})
        
        split_method = training.get("dataSplit", {}).get("method", "")
        split_used = evaluation.get("splitUsed", "")
        
        if split_method == "chronological" and split_used == "full":
            report.add(ValidationResult(
                "RM-050", Severity.WARNING,
                "Evaluation on 'full' dataset with chronological split may indicate data leakage.",
                json_path="evaluation.splitUsed"
            ))


# =============================================================================
# MAIN VALIDATOR
# =============================================================================

def validate(artifact_path: str, schema_dir: Optional[str] = None) -> ValidationReport:
    """
    Validate a HydroModelSpec model artifact.
    
    Args:
        artifact_path: Path to JSON model artifact file.
        schema_dir: Optional path to schemas directory.
    
    Returns:
        ValidationReport with all findings.
    """
    report = ValidationReport()
    
    # Load artifact
    try:
        with open(artifact_path, "r") as f:
            artifact = json.load(f)
    except json.JSONDecodeError as e:
        report.add(ValidationResult(
            "LOAD-001", Severity.ERROR,
            f"Invalid JSON: {e}"
        ))
        return report
    except FileNotFoundError:
        report.add(ValidationResult(
            "LOAD-002", Severity.ERROR,
            f"File not found: {artifact_path}"
        ))
        return report
    
    report.artifact_id = artifact.get("id", "<unknown>")
    report.spec_version = artifact.get("specVersion", "<unknown>")
    
    # Layer 1: Schema validation
    schema_validator = SchemaValidator()
    
    # Layer 2: Instance validation
    data_validator = DataValidator(schema_dir)
    data_validator.validate_instance(artifact, report)
    
    # Layer 3: Rule-based validation
    rule_module = RuleModule()
    rule_module.validate_rules(artifact, report)
    
    return report


def validate_dict(artifact: dict, schema_dir: Optional[str] = None) -> ValidationReport:
    """Validate a model artifact from a Python dict."""
    report = ValidationReport()
    report.artifact_id = artifact.get("id", "<unknown>")
    report.spec_version = artifact.get("specVersion", "<unknown>")
    
    data_validator = DataValidator(schema_dir)
    data_validator.validate_instance(artifact, report)
    
    rule_module = RuleModule()
    rule_module.validate_rules(artifact, report)
    
    return report


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m validator <artifact.json> [--schema-dir <path>]")
        print("       python -m validator --batch <dir>")
        sys.exit(1)
    
    schema_dir = None
    if "--schema-dir" in sys.argv:
        idx = sys.argv.index("--schema-dir")
        schema_dir = sys.argv[idx + 1]
        sys.argv.pop(idx)
        sys.argv.pop(idx)
    
    if sys.argv[1] == "--batch":
        # Batch validation
        directory = sys.argv[2] if len(sys.argv) > 2 else "."
        json_files = sorted(Path(directory).glob("*.json"))
        
        if not json_files:
            print(f"No JSON files found in {directory}")
            sys.exit(1)
        
        all_valid = True
        for filepath in json_files:
            report = validate(str(filepath), schema_dir)
            print(report.summary())
            if not report.is_valid:
                all_valid = False
                for r in report.errors:
                    print(f"  ERROR [{r.rule_code}] {r.json_path}: {r.message}")
        
        sys.exit(0 if all_valid else 1)
    
    else:
        # Single file validation
        artifact_path = sys.argv[1]
        report = validate(artifact_path, schema_dir)
        
        print(report.summary())
        print()
        
        for r in report.results:
            icon = {"error": "✗", "warning": "⚠", "info": "✓"}[r.severity.value]
            print(f"  {icon} [{r.rule_code}] {r.json_path or '(root)'}: {r.message}")
        
        print()
        print(json.dumps(report.to_dict(), indent=2))
        
        sys.exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
