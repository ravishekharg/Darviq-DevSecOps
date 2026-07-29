# DevSecOps CI/CD Pipeline

![Pipeline](https://github.com/ravishekharg/devsecops-pipeline/actions/workflows/devsecops-pipeline.yaml/badge.svg)
![Trivy](https://img.shields.io/badge/Security-Trivy-blue?logo=aqua)
![OPA](https://img.shields.io/badge/Policy-OPA%2FGatekeeper-orange)
![SBOM](https://img.shields.io/badge/SBOM-Syft-purple)

A production-grade DevSecOps pipeline implementing "shift-left" security —
every vulnerability is caught before it reaches production. A small Flask
demo app is used as the artifact that flows through the pipeline: it is
scanned, built, container-scanned, given an SBOM, and validated against
Kubernetes admission policy before it is considered deployable.

## Pipeline Stages

| Stage | Tool | Purpose |
|-------|------|---------|
| SAST | Bandit + Semgrep | Python code security analysis |
| SCA | Safety | Dependency vulnerability scanning |
| IaC Scan | Checkov | Terraform + K8s manifest security |
| Container Scan | Trivy | Image CVE scanning (CRITICAL = block) |
| SBOM | Syft | Software Bill of Materials (SPDX + CycloneDX) |
| Policy | OPA | Kubernetes manifest policy enforcement |
| Admission Control | Gatekeeper | Runtime policy enforcement on cluster |
| Report | `scripts/security-report.py` | Consolidates Bandit/Safety findings into a Markdown summary |

These stages are implemented as GitHub Actions jobs in
[`.github/workflows/devsecops-pipeline.yaml`](.github/workflows/devsecops-pipeline.yaml),
which runs on every push/PR to `main`/`develop`. A separate
[`.github/workflows/scheduled-scan.yaml`](.github/workflows/scheduled-scan.yaml)
runs a full filesystem vulnerability scan weekly.

## Security Gates

- CRITICAL CVEs in container image → **pipeline fails**
- Privileged containers → **OPA policy / Gatekeeper blocks deployment**
- Missing resource limits → **OPA policy / Gatekeeper blocks deployment**
- Containers running as root → **Gatekeeper blocks deployment**
- Hardcoded secrets → **Trivy FS scan catches them**
- Insecure IaC → **Checkov reports to GitHub Security tab**

## Prerequisites

To run the pipeline stages locally you'll need:

- Python 3.12+ (the app and tooling target this version)
- Docker (to build the container image)
- [OPA](https://www.openpolicyagent.org/docs/latest/#running-opa) (`opa` CLI) for policy evaluation
- [Trivy](https://aquasecurity.github.io/trivy/) for filesystem/image scanning
- [Syft](https://github.com/anchore/syft) for SBOM generation
- [Terraform](https://developer.hashicorp.com/terraform) 1.x for the IaC sample
- A Kubernetes cluster with [Gatekeeper](https://open-policy-agent.github.io/gatekeeper/) installed, if you want to test admission control

## Folder Structure

```
.
├── app/                          # Flask demo application
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── kubernetes/
│   ├── deployment.yaml           # Hardened sample Deployment manifest
│   └── gatekeeper/
│       ├── constraint-templates/ # OPA Gatekeeper ConstraintTemplates
│       └── constraints/          # Gatekeeper Constraints (bind templates to workloads)
├── opa/
│   └── policies/                 # Standalone OPA/Rego policies (CI-time `opa eval`)
├── scripts/
│   └── security-report.py        # Consolidates Bandit/Safety results into a Markdown report
├── terraform/
│   └── main.tf                   # Sample hardened S3 bucket for Checkov IaC scanning
└── .github/workflows/            # CI pipeline + scheduled scan definitions
```

## Quick Start

```bash
git clone https://github.com/ravishekharg/devsecops-pipeline
cd devsecops-pipeline

# Run OPA policy check locally
opa eval --data opa/policies/ \
         --input kubernetes/deployment.yaml \
         "data.kubernetes.deny"

# Run Trivy locally
trivy fs . --severity HIGH,CRITICAL

# Run Bandit locally
pip install bandit && bandit -r app/

# Generate SBOM locally
syft app/ --output table
```

## Architecture

Security is enforced at every layer:
- **Code** — SAST with Bandit catches insecure patterns
- **Dependencies** — Safety blocks known vulnerable packages
- **Infrastructure** — Checkov ensures IaC follows CIS benchmarks
- **Container** — Trivy blocks CRITICAL CVEs before push
- **Manifest** — OPA validates K8s YAMLs before apply
- **Runtime** — Gatekeeper enforces policies on the live cluster

---

## How to Use This Repo

```bash
# 1. Create and push the repo
git init devsecops-pipeline
cd devsecops-pipeline
# copy all files above into correct paths
git add .
git commit -m "feat: complete DevSecOps pipeline with Trivy, OPA, Gatekeeper, SBOM"
git push -u origin main

# 2. GitHub Actions runs automatically on push
# Check: Actions tab → DevSecOps Pipeline

# 3. Security findings appear in:
# Security tab → Code scanning → Trivy / Checkov alerts

# 4. SBOM artifacts downloadable from Actions → Artifacts
```
