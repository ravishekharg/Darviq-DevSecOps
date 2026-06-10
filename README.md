```markdown
# DevSecOps CI/CD Pipeline

![Pipeline](https://github.com/ravishekharg/devsecops-pipeline/actions/workflows/devsecops-pipeline.yaml/badge.svg)
![Trivy](https://img.shields.io/badge/Security-Trivy-blue?logo=aqua)
![OPA](https://img.shields.io/badge/Policy-OPA%2FGatekeeper-orange)
![SBOM](https://img.shields.io/badge/SBOM-Syft-purple)

A production-grade DevSecOps pipeline implementing "shift-left" security —
every vulnerability is caught before it reaches production.

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

## Security Gates

- CRITICAL CVEs in container image → **pipeline fails**
- Privileged containers → **OPA policy blocks deployment**  
- Missing resource limits → **OPA policy blocks deployment**
- Hardcoded secrets → **Trivy FS scan catches them**
- Insecure IaC → **Checkov reports to GitHub Security tab**

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
```

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