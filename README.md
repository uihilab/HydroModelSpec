# HydroModelSpec

**A Vendor-Neutral Specification for Portable, Privacy-Preserving Machine Learning Model Exchange in Operational Hydrology**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![JSON Schema](https://img.shields.io/badge/JSON%20Schema-Draft%202020--12-green.svg)](https://json-schema.org/draft/2020-12/schema)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)

**Reference Platform:** [Hydro Lab AI](https://hydroinformatics.tulane.edu/lab/hydro-ai-hub/) | **Platform Source:** [GitHub](https://github.com/uihilab/AI-HYDRO-HUB)

---

## The Problem

Trained hydrological ML models are **trapped**. A model trained in PyTorch can't be loaded in TensorFlow. A model's training provenance — what data it saw, how it was split, what metrics it achieved — is nowhere standardized. Most critically, **no mechanism exists to attest that a model was trained without data leaving the originating device** — blocking privacy-preserving model sharing across agencies governed by FISMA, CISA, and data sovereignty regulations.

## The Solution

**HydroModelSpec** defines how a trained ML model is packaged — together with its architecture, training provenance, performance benchmarks, execution requirements, and privacy attestation — into a single, portable, **machine-verifiable** artifact that any compliant platform can load, validate, and execute.

### Key Features

- **🔒 Privacy Attestation** — First ML model exchange format with machine-readable zero-trust provenance
- **📦 Portable Artifacts** — One artifact, any platform: NumPy, PyTorch, TensorFlow, ONNX, WebGPU
- **🌊 Domain Profiles** — Streamflow, water level, flood inundation, reservoir operations
- **✅ Validator** — Enforcement-grade structural and semantic conformance checking
- **🤝 GIFIS Companion** — Completes the exchange ecosystem: GIFIS moves data; HydroModelSpec moves models

---

## Quick Start

### Installation

```bash
pip install jsonschema
```

### Validate a Model Artifact

```bash
# CLI
python -m validator examples/valid_lstm_streamflow.json

# Python
from validator import validate
report = validate("examples/valid_lstm_streamflow.json")
print(report.summary())
```

### Output

```
[PASS] hms-lstm-belle-chasse-20250215 (hms-streamflow@1.0) - 0 errors, 0 warnings

  ✓ [DV-100] (root): Artifact conforms to HydroModelSpec Core Schema.
```

---

## Specification Architecture

```
HydroModelSpec
├── Core Schema          — Universal model metadata (id, architecture, training, evaluation, privacy, weights)
├── Domain Profiles      — Task-specific constraints
│   ├── Streamflow       — NWM post-processing (NSE, RMSE, KGE, PBIAS required)
│   ├── Water Level      — Stage forecasting (vertical datum, tidal influence)
│   ├── Inundation       — Flood mapping (precision, recall, F1, CSI)
│   └── Reservoir        — Operations (inflow/release prediction)
├── Portable Documents   — Exchange packaging
│   ├── Model Card       — Human + machine readable documentation
│   ├── Execution Manifest — Runtime dependencies and requirements
│   ├── Privacy Attestation — Zero-trust training provenance
│   └── Benchmark Report — Standardized baseline comparison
└── Validator            — Enforcement engine (Schema + Data + Rule layers)
```

---

## Project Structure

```
hydromodelspec/
├── schemas/
│   ├── core/
│   │   └── core.schema.json          # Core Schema (Tables 1-6 in paper)
│   └── profiles/
│       ├── streamflow.schema.json     # Streamflow Post-Processing Profile
│       ├── waterlevel.schema.json     # Water Level Forecasting Profile
│       ├── inundation.schema.json     # Flood Inundation Profile
│       └── reservoir.schema.json      # Reservoir Operations Profile
├── validator/
│   ├── __init__.py
│   ├── __main__.py
│   └── validate.py                    # 3-layer validator (Schema + Data + Rules)
├── examples/
│   ├── valid_lstm_streamflow.json     # ✅ Complete LSTM artifact (Belle Chasse)
│   ├── valid_cnn_waterlevel.json      # ✅ CNN water level artifact
│   ├── minimal_valid.json             # ✅ Minimal conformant artifact
│   └── invalid_artifact.json          # ✗ Intentional violations
├── tests/
│   └── test_validator.py              # 15+ test cases
├── docs/
│   └── (specification documentation)
├── pyproject.toml
├── LICENSE                            # Apache 2.0
├── .gitignore
└── README.md
```

---

## Privacy Attestation

The **first machine-readable privacy attestation** for ML model exchange:

```json
{
  "privacy": {
    "trainedLocally": true,
    "dataTransmitted": false,
    "attestationMethod": "platform_verified",
    "platformId": "hydrolabai-v1.0",
    "datasetHash": "sha256:a1b2c3...",
    "weightsHash": "sha256:f1e2d3...",
    "attestedAt": "2025-02-15T14:32:00Z",
    "compliance": ["FISMA", "CISA"]
  }
}
```

**Three attestation levels:**
| Method | Trust Level | Mechanism |
|---|---|---|
| `self_declared` | Basic | Producer asserts privacy properties |
| `platform_verified` | Standard | Training platform (e.g., Hydro Lab AI) generates attestation |
| `tee_attested` | Highest | Hardware Trusted Execution Environment provides cryptographic proof |

---

## Validation Rules

The validator enforces 15+ rule codes across three layers:

| Code | Layer | Severity | Description |
|---|---|---|---|
| `SV-001` | Schema | Error | jsonschema library missing |
| `DV-003` | Data | Error | Schema conformance violation |
| `RM-001` | Rules | Warning | Model ID missing `hms-` prefix |
| `RM-002` | Rules | Error | specVersion format invalid |
| `RM-003` | Rules | Error | updatedAt before createdAt |
| `RM-010` | Rules | Error | NSE exceeds 1.0 |
| `RM-011` | Rules | Error | Negative RMSE |
| `RM-020` | Rules | Error | Privacy inconsistency (local + transmitted) |
| `RM-030` | Rules | Error | Invalid SHA-256 hash format |
| `RM-040` | Rules | Warning | Data split ratios don't sum to 1.0 |
| `RM-050` | Rules | Warning | Evaluation on full data with chronological split |

---

## Example: Complete Model Artifact

See [`examples/valid_lstm_streamflow.json`](examples/valid_lstm_streamflow.json) for a full artifact generated by Hydro Lab AI, including:

- LSTM architecture with 32 hidden units
- Training provenance (Adam, 30 epochs, 168h lookback, chronological split)
- Four hydrological metrics (NSE 0.858, RMSE 740, KGE 0.844, PBIAS -1.8%)
- NWM baseline comparison
- Privacy attestation (trained locally, platform-verified)
- NumPy weight artifact with SHA-256 integrity hash

---

## Companion Standards & Platforms

| Standard/Platform | Scope | Relationship |
|---|---|---|
| **GIFIS** | Hydrological *data* exchange | GIFIS moves data; HydroModelSpec moves models |
| **Hydro Lab AI** | Privacy-preserving ML platform | Reference implementation; generates spec-compliant artifacts |
| **ONNX** | Computational graph portability | HydroModelSpec adds provenance, metrics, privacy on top |
| **Model Cards** | Human documentation | HydroModelSpec makes documentation machine-verifiable |
| **HydroShare** | Data/model repository | HydroModelSpec artifacts can be published to HydroShare |

> **Hydro Lab AI** ([live platform](https://hydroinformatics.tulane.edu/lab/hydro-ai-hub/) | [source](https://github.com/uihilab/AI-HYDRO-HUB)) is a no-code, privacy-preserving browser-based platform that automatically generates HydroModelSpec-compliant model artifacts when users train CNN, LSTM, TCN, or hybrid deep learning models for NOAA National Water Model post-processing. All computation executes locally — your data never leaves your device.

---

## Running Tests

```bash
pip install jsonschema pytest
python -m pytest tests/ -v
```

---

## Citation

If you use HydroModelSpec in your research, please cite:

```bibtex
@article{singh2025hydromodelspec,
  title={HydroModelSpec: A Vendor-Neutral Specification for Portable, Privacy-Preserving Machine Learning Model Exchange in Operational Hydrology},
  author={Singh, Nikhil and Sermet, Yusuf and Sajja, Ramteja and Demir, Ibrahim},
  year={2025},
  institution={Department of River-Coastal Science and Engineering, Tulane University}
}
```

If you use the Hydro Lab AI reference platform, please also cite:

```bibtex
@article{singh2025hydrolabai,
  title={Your Data Never Leaves: Privacy-Preserving Deep Learning and WebGPU AI Assistance for Operational Hydrology},
  author={Singh, Nikhil and Sermet, Yusuf and Sajja, Ramteja and Demir, Ibrahim},
  year={2025},
  url={https://hydroinformatics.tulane.edu/lab/hydro-ai-hub/}
}
```

---

## Contributing

Contributions are welcome! Please see our [contributing guidelines](docs/CONTRIBUTING.md) and submit pull requests against the `main` branch.

**RFC Process:** All specification changes go through public Requests for Comments. Open an issue with the `rfc` label to propose changes.

---

## Authors

- **Nikhil Singh** — Lead Developer & Specification Design — nsingh4@tulane.edu
- **Yusuf Sermet** — Specification Design & Review
- **Ramteja Sajja** — Specification Design & Review
- **Ibrahim Demir** — Project Direction, Supervision & Funding

Department of River-Coastal Science and Engineering, Tulane University

## Funding

This research was funded by the **U.S. Geological Survey (USGS)**.

---

*HydroModelSpec is an open standard. Your data never leaves. Your models go everywhere.*
