# OrthoCloud Step 1 — Scaffold Design

**Date:** 2026-04-17
**Scope:** File structure setup + DevOps foundations for Step 1 (DICOM Upload)
**Phase:** 1.5 — synthetic/de-identified data only, no AWS setup yet

---

## 1. File Structure

Full tree from README repository structure section, created in one pass. All application logic files are wired skeletons (Approach B) — `main.py` imports and registers all routers; route handlers return `{"status": "not implemented"}`; all pipeline files are empty stubs.

```
orthocloud-repo/
├── README.md                          # already exists
├── .gitignore                         # prevents secrets/packages/temp files from being committed
├── .env.example                       # environment variable template (no real values)
├── docker-compose.yml                 # orchestrates backend + GPU for local dev
├── .github/
│   ├── dependabot.yml                 # automated dependency CVE tracking
│   ├── CODEOWNERS                     # enforces review on backend/ and .github/
│   └── workflows/
│       ├── claude.yml                 # existing — @claude mention handler
│       ├── claude-code-review.yml     # existing — @claude review
│       ├── claude-security-review.yml # existing — @claude security
│       ├── claude-pr-deep-review.yml  # existing — @claude deep review
│       ├── claude-scheduled-compliance-scan.yml  # existing — compliance scan
│       └── ci.yml                    # NEW — pytest + ruff on every PR to develop
└── backend/
    ├── Dockerfile                     # builds the FastAPI backend container
    ├── requirements.txt               # pinned Python dependencies
    └── app/
        ├── main.py                    # FastAPI app entry point; registers all routers
        ├── routes/
        │   ├── __init__.py
        │   └── segment.py             # POST /segment, GET /structures — stubs only
        └── pipeline/
            ├── __init__.py
            ├── dicom_io.py            # Step 2: SimpleITK DICOM folder → NIfTI
            ├── segmentation.py        # Step 3: MONAI Deploy + TotalSegmentator
            ├── extraction.py          # Step 4: structure name → NIfTI mask file
            └── structures.py          # Step 4: STRUCTURE_MAP constant
```

---

## 2. Wired Skeleton — Application Files

### `backend/app/main.py`
Creates the FastAPI app and immediately includes the segment router. No logic — the router import is the only non-boilerplate content.

```python
from fastapi import FastAPI
from app.routes import segment

app = FastAPI(title="OrthoCloud")
app.include_router(segment.router)
```

### `backend/app/routes/segment.py`
Defines the router with both endpoints from the API reference. Returns `{"status": "not implemented"}` until Step 1 logic is added.

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/structures")
def get_structures():
    return {"status": "not implemented"}

@router.post("/segment")
def post_segment():
    return {"status": "not implemented"}
```

### `backend/app/pipeline/*.py`
All four pipeline files (`dicom_io.py`, `segmentation.py`, `extraction.py`, `structures.py`) are empty — no imports, no content. Each is filled when its step is implemented.

---

## 3. Docker — Local Dev Only

No AWS infrastructure in Phase 1.5. Two files only:

- **`docker-compose.yml`** — orchestrates `backend` service; GPU stub service placeholder for Phase 2. Reads from `.env` file.
- **`backend/Dockerfile`** — builds the FastAPI image. Multi-stage not required at this scale; single stage with Python slim base.

---

## 4. Git Branching Strategy

```
main        → production-ready code (branch-protected, requires PR + review)
staging     → staging environment (auto-deploy in Phase 2)
develop     → integration branch (all feature PRs target here)
feature/*   → short-lived feature branches (branch off develop, PR back to develop)
hotfix/*    → urgent fixes (branch off main, PR to main + develop)
```

Branches `develop`, `staging`, and `feature/scaffold-step1` are initialised as part of this scaffold. All implementation work for Step 1 happens on `feature/scaffold-step1`.

---

## 5. CI/CD Gaps Closed

### `.gitignore`
Prevents accidental commits of secrets and locally installed packages. Covers:
- Python virtual environments: `.venv/`, `venv/`, `env/`
- Python bytecode: `__pycache__/`, `*.pyc`, `*.pyo`, `*.egg-info/`
- Test and lint caches: `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`
- Environment files: `.env` (template `.env.example` is committed; real `.env` is not)
- Temp pipeline output: `tmp/`, `*.nii`, `*.nii.gz`, `*.dcm`, `*.zip`
- Editor and OS noise: `.idea/`, `.vscode/`, `.DS_Store`

### `ci.yml` — Automated PR workflow
Fires on every PR opened or updated against `develop`. Runs:
1. `pip install -r backend/requirements.txt`
2. `ruff check backend/` — linting
3. `pytest backend/` — unit tests (no tests yet; workflow scaffolded so it runs clean)

Fail-fast: lint failure blocks merge; test failure blocks merge.

### `dependabot.yml`
Checks `backend/requirements.txt` weekly for dependency updates and CVEs. Opens PRs automatically. Creates an auditable vulnerability-response record for IEC 62304 software lifecycle compliance.

### `CODEOWNERS`
Requires review from `@bpetselis01` on any PR that touches:
- `backend/` — application code
- `.github/` — workflow and CI configuration

---

## 6. Comment Style — All New Files

Every new file follows the step-numbered inline comment pattern used in existing workflows. Each section comment explains **what** it does and **why** — not just labels. Example from `docker-compose.yml`:

```yaml
# Step 1: Define the backend service
# FastAPI app — handles DICOM upload, triggers segmentation pipeline
```

This applies to: `.gitignore`, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `ci.yml`, `dependabot.yml`, `CODEOWNERS`, `main.py`, `segment.py`.

---

## 7. Out of Scope (Phase 2)

- AWS ECR, ECS, Fargate
- Multi-account AWS Organisation (AU/EU/US)
- Service Control Policies (SCPs) for data sovereignty
- Staging auto-deploy pipeline
- AWS Secrets Manager
- Branch protection rule configuration (done manually in GitHub UI)

---

## Implementation Order

1. Create git branches: `develop`, `staging`, checkout `feature/scaffold-step1`
2. Create `.gitignore`
3. Create `.env.example`
4. Create `docker-compose.yml`
5. Create `backend/Dockerfile`
6. Create `backend/requirements.txt`
7. Create `backend/app/main.py`
8. Create `backend/app/routes/__init__.py` and `segment.py`
9. Create `backend/app/pipeline/__init__.py` and four empty stubs
10. Create `.github/CODEOWNERS`
11. Create `.github/dependabot.yml`
12. Create `.github/workflows/ci.yml`
