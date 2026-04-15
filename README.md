# OrthoCloud — MVP

> Cloud-based CT segmentation pipeline: upload a DICOM CT series, select an anatomical structure, receive a segmentation mask openable directly in 3D Slicer.

---

## Contents

- [What This Builds](#what-this-builds)
- [MVP Scope](#mvp-scope)
- [Software Architecture](#software-architecture)
- [Tech Stack](#tech-stack)
- [Pipeline: Step by Step](#pipeline-step-by-step)
  - [Step 1 — DICOM Upload](#step-1--dicom-upload)
  - [Step 2 — DICOM → NIfTI Conversion](#step-2--dicom--nifti-conversion-simpleitk)
  - [Step 3 — Segmentation via MONAI Deploy + TotalSegmentator](#step-3--segmentation-via-monai-deploy--totalsegmentator)
  - [Step 4 — Structure Extraction](#step-4--structure-extraction-post-processing)
  - [Step 5 — Output: NIfTI Mask](#step-5--output-nifti-mask)
- [API Reference](#api-reference)
  - [GET /structures](#get-structures)
  - [POST /segment](#post-segment)
- [Repository Structure](#repository-structure)
- [Local Setup](#local-setup)
  - [Prerequisites](#prerequisites)
  - [Run with Docker](#run-with-docker)
  - [Run without Docker (dev)](#run-without-docker-dev)
  - [Test the Pipeline](#test-the-pipeline)
- [Output Format Notes](#output-format-notes)
- [Post-MVP Roadmap](#post-mvp-roadmap)
- [References](#references)

---

## What This Builds

OrthoCloud MVP is a backend API that accepts a CT scan (multi-slice DICOM), runs automated anatomical segmentation using TotalSegmentator (deployed as a MONAI Deploy App), and returns a NIfTI mask (`.nii.gz`) for the selected structure — e.g. the right femur. The mask opens natively in 3D Slicer as a label map, with the option to generate a surface mesh inside Slicer in one click.

This is intentionally scoped to the core pipeline: no frontend, no authentication, no cloud infra. Just the inference loop, working end-to-end locally via Docker.

---

## MVP Scope

| # | Capability | Status |
|---|---|---|
| 1 | Accept a DICOM CT series upload (multi-slice) | MVP |
| 2 | Select anatomical structure by name (e.g. `right_femur`) | MVP |
| 3 | Convert DICOM → NIfTI and preprocess | MVP |
| 4 | Run segmentation via TotalSegmentator in a MONAI Deploy App | MVP |
| 5 | Extract the selected structure mask from multi-label output | MVP |
| 6 | Return binary NIfTI mask (`.nii.gz`) openable in 3D Slicer | MVP |
| 7 | Optional: return STL surface mesh via VTK marching cubes | Post-MVP |
| 8 | Interactive mask refinement (nnInteractive) | Post-MVP |
| 9 | Web viewer (trame-slicer) | Post-MVP |

---

## Software Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT                                   │
│   POST /segment                                                 │
│   - multipart upload: DICOM folder (zipped)                     │
│   - body: { "structure": "right_femur" }                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────────────┐
│                     FastAPI BACKEND                             │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │  DICOM I/O  │───▶│ MONAI Deploy │───▶│  Post-processing   │  │
│  │  (SimpleITK)│    │     App      │    │  (structure filter)│  │
│  └─────────────┘    └──────┬───────┘    └─────────┬──────────┘  │
│                            │                      │             │
│                   ┌────────▼────────┐    ┌────────▼──────────┐  │
│                   │TotalSegmentator │    │  NIfTI output     │  │
│                   │  (104-class     │    │  (.nii.gz mask)   │  │
│                   │   nnU-Net)      │    │                   │  │
│                   └─────────────────┘    └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼ download
┌─────────────────────────────────────────────────────────────────┐
│               3D SLICER (local, user's machine)                 │
│                                                                 │
│   File > Add Data > right_femur.nii.gz                          │
│   → Loads as Segmentation node                                  │
│   → "Show 3D" generates surface mesh automatically             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| API framework | **FastAPI** (Python) | Async, fast, auto-docs at `/docs` |
| DICOM → NIfTI | **SimpleITK** | Standard in medical imaging; handles DICOM metadata, spacing, orientation (LPS/RAS) correctly |
| Segmentation model | **TotalSegmentator** | 104 pre-trained anatomical structures including all major bones; NIfTI output; ~1 min on GPU; no training required |
| Deployment wrapper | **MONAI Deploy SDK** | Wraps the inference pipeline with DICOM-native operators; production-grade operator chaining |
| Containerisation | **Docker + NVIDIA Container Toolkit** | GPU passthrough; reproducible environment; matches cloud GPU instance requirements |
| Output format | **NIfTI** (`.nii.gz`) | Natively supported by 3D Slicer, ITK, MONAI, nnU-Net — the universal interchange format in medical imaging |

**Why TotalSegmentator over VISTA3D for the MVP:**
TotalSegmentator has a direct Python API (`totalsegmentator(input, output)`) and known bone coverage tested against clinical data. VISTA3D (MONAI's native foundation model) is the natural upgrade path once the pipeline is proven — it supports 127 classes and class-prompt/interactive modes, both needed for a production system.

---

## Pipeline: Step by Step

### Step 1 — DICOM Upload

The client POSTs a ZIP of a DICOM CT series to `/segment`.

```
POST /segment
Content-Type: multipart/form-data

file: <ct_series.zip>
structure: "right_femur"
```

FastAPI writes the ZIP to a temp directory and extracts it. A DICOM series is a folder of `.dcm` slice files — one file per axial slice, typically 200–500 slices for a full CT.

**Why ZIP?** A CT series is 200–500 files. A single ZIP upload is simpler than handling multi-file uploads and avoids partial upload issues.

---

### Step 2 — DICOM → NIfTI Conversion (SimpleITK)

SimpleITK reads the DICOM series and writes a single 3D NIfTI volume. This step is critical because:

- DICOM stores slices as 2D images with metadata; NIfTI stores the full 3D volume with voxel spacing embedded
- TotalSegmentator and MONAI expect NIfTI (or MHA/NRRD) — not raw DICOM
- SimpleITK correctly reconstructs voxel spacing and orientation from DICOM metadata, avoiding resampling artefacts

```python
# backend/app/pipeline/dicom_io.py
import SimpleITK as sitk

def dicom_to_nifti(dicom_dir: str, output_path: str) -> str:
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    sitk.WriteImage(image, output_path)
    return output_path
```

Output: `ct_volume.nii.gz` — a 3D float32 volume in Hounsfield Units (HU).

---

### Step 3 — Segmentation via MONAI Deploy + TotalSegmentator

The NIfTI volume is passed to a **MONAI Deploy App** that wraps TotalSegmentator.

**What MONAI Deploy adds:**
- Operator graph: each processing step is an `Operator` with defined inputs/outputs
- DICOM ingestion operators (for production DICOM PACS integration later)
- Structured app execution — testable, loggable, reproducible

**What TotalSegmentator does:**
- Accepts the NIfTI volume
- Runs a pre-trained nnU-Net model
- Outputs a **multi-label NIfTI mask** — a 3D integer volume where each voxel value corresponds to an anatomical structure index
  - e.g. `0` = background, `5` = right_femur, `6` = left_femur, `29` = right_hip, etc.
- Full structure list: [TotalSegmentator class map](https://github.com/wasserth/TotalSegmentator#class-details)

```python
# backend/app/pipeline/segmentation.py
from totalsegmentator.python_api import totalsegmentator

def run_segmentation(input_nifti: str, output_dir: str) -> str:
    """
    Runs TotalSegmentator on the input NIfTI volume.
    Returns path to multi-label segmentation mask.
    """
    totalsegmentator(input=input_nifti, output=output_dir, task="total")
    return output_dir  # contains individual structure .nii.gz files
```

**GPU note:** TotalSegmentator uses ~8 GB VRAM. On CPU it runs but takes ~10–20 minutes. For MVP local development, a GPU is recommended but not required.

---

### Step 4 — Structure Extraction (Post-processing)

TotalSegmentator outputs **one NIfTI file per structure** into the output directory (e.g. `right_femur.nii.gz`, `left_femur.nii.gz`, etc.). The requested structure is simply selected from that folder.

```python
# backend/app/pipeline/extraction.py
import os

# Maps user-facing names to TotalSegmentator output filenames
STRUCTURE_MAP = {
    "right_femur": "femur_right.nii.gz",
    "left_femur": "femur_left.nii.gz",
    "right_hip": "hip_right.nii.gz",
    "left_hip": "hip_left.nii.gz",
    "right_tibia": "tibia_right.nii.gz",
    "left_tibia": "tibia_left.nii.gz",
    "right_fibula": "fibula_right.nii.gz",
    "left_fibula": "fibula_left.nii.gz",
    "vertebrae_L1": "vertebrae_L1.nii.gz",
    # ... full map from TotalSegmentator class list
}

def extract_structure(output_dir: str, structure_name: str) -> str:
    filename = STRUCTURE_MAP.get(structure_name)
    if not filename:
        raise ValueError(f"Unknown structure: {structure_name}. "
                         f"Valid options: {list(STRUCTURE_MAP.keys())}")
    path = os.path.join(output_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Segmentation output not found: {path}")
    return path
```

The result is a **binary NIfTI mask**: voxels belonging to the right femur = `1`, everything else = `0`.

---

### Step 5 — Output: NIfTI Mask

The binary `.nii.gz` mask is returned as a file download.

```
Response: 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="right_femur.nii.gz"
```

**Opening in 3D Slicer:**
1. `File` > `Add Data` > select `right_femur.nii.gz`
2. In the "Add Data" dialog, check "Show Options" and set type to **Segmentation** (or leave as Label Map Volume)
3. Click OK — the femur mask loads as a coloured 3D overlay on the CT
4. In the Segment Editor, click **Show 3D** — Slicer generates a surface mesh automatically

No additional tools or plugins required. NIfTI is natively supported by 3D Slicer.

---

## API Reference

### `GET /structures`

Returns the list of supported anatomical structures.

```json
{
  "structures": [
    "right_femur",
    "left_femur",
    "right_tibia",
    "left_tibia",
    "right_hip",
    "left_hip",
    "vertebrae_L1",
    "..."
  ]
}
```

### `POST /segment`

Upload a CT series and request segmentation of a specific structure.

**Request:**
```
Content-Type: multipart/form-data

file: <ct_series.zip>       # ZIP of DICOM .dcm files
structure: "right_femur"    # from /structures list
```

**Response (success):**
```
200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="right_femur.nii.gz"

<binary NIfTI file>
```

**Response (error):**
```json
{
  "detail": "Unknown structure: right_knee. Valid options: [...]"
}
```

---

## Repository Structure

```
orthocloud/
├── README.md
├── docker-compose.yml          # Orchestrates backend + GPU
├── .env.example                # Environment variable template
│
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py             # FastAPI app, router registration
        ├── routes/
        │   └── segment.py      # POST /segment, GET /structures
        └── pipeline/
            ├── dicom_io.py     # SimpleITK: DICOM folder → NIfTI
            ├── segmentation.py # MONAI Deploy App wrapping TotalSegmentator
            ├── extraction.py   # Structure name → NIfTI mask file
            └── structures.py   # STRUCTURE_MAP constant
```

---

## Local Setup

### Prerequisites

- Docker Desktop with GPU support (NVIDIA Container Toolkit)
- Or: Python 3.10+, pip, a GPU with ≥8 GB VRAM (CPU fallback is slow but works)

### Run with Docker

```bash
git clone https://github.com/<you>/orthocloud-repo
cd orthocloud-repo
docker-compose up --build
```

API available at `http://localhost:8000`
Auto-generated docs at `http://localhost:8000/docs`

### Run without Docker (dev)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Test the Pipeline

```bash
# 1. Check available structures
curl http://localhost:8000/structures

# 2. Upload a CT series and segment the right femur
curl -X POST http://localhost:8000/segment \
  -F "file=@ct_series.zip" \
  -F "structure=right_femur" \
  --output right_femur.nii.gz

# 3. Open right_femur.nii.gz in 3D Slicer
```

---

## Output Format Notes

| Format | How to open in 3D Slicer | Generated by |
|---|---|---|
| `.nii.gz` (NIfTI mask) | `File > Add Data` → set type to Segmentation | MVP — TotalSegmentator direct output |
| `.seg.nrrd` (Slicer segmentation) | `File > Add Data` | Post-MVP — convert with SimpleITK |
| `.stl` (surface mesh) | `File > Add Data` → loads as 3D Model | Post-MVP — VTK marching cubes on the NIfTI mask |
| `.gltf` (web mesh) | Not Slicer; for OrthoCloud web viewer | Post-MVP — VTK export |

**Recommendation for MVP:** NIfTI mask. It is the lowest-complexity output, requires no additional processing, and Slicer's built-in Segment Editor can generate a surface mesh from it interactively in one click.

---

## Post-MVP Roadmap

| Phase | Feature | Key Technology |
|---|---|---|
| 2 | STL mesh output from segmentation mask | VTK marching cubes (Python `vtk` package) |
| 2 | Swap to VISTA3D for MONAI-native inference | MONAI VISTA3D (127 classes, class-prompt mode) |
| 3 | Interactive mask refinement in browser | nnInteractive + slicer-nninteractive extension |
| 3 | Cloud-hosted 3D Slicer viewer | trame-slicer (Kitware) |
| 4 | DICOM PACS integration | MONAI Deploy DICOM operators |
| 4 | GPU autoscaling | NVIDIA MONAI Cloud API |

---

## References

- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator) — Wasserthal et al., radiology.ucsf.edu
- [MONAI Deploy SDK](https://docs.monai.io/projects/monai-deploy-app-sdk) — NVIDIA/Project MONAI
- [MONAI Framework](https://github.com/Project-MONAI/MONAI)
- [VISTA3D](https://github.com/Project-MONAI/VISTA) — MONAI's 127-class foundation model
- [SimpleITK](https://simpleitk.org) — medical image I/O and preprocessing
- [VTK](https://github.com/Kitware/VTK) — mesh generation from segmentation masks
- [3D Slicer](https://www.slicer.org) — open-source medical image viewer
- [trame-slicer](https://github.com/KitwareMedical/trame-slicer) — cloud-deployable Slicer
- [nnInteractive](https://github.com/MIC-DKFZ/nnInteractive) — interactive 3D segmentation refinement
