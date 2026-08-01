# -*- coding: utf-8 -*-
"""Generates Darviq_DevSecOps_High_Level_Design.docx from the docx_builder helper.
Run from the Docs/ directory (or anywhere, since it uses an absolute save path).
"""
from docx_builder import DesignDoc

VERSION = "1.0"
DATE = "July 31, 2026"

doc = DesignDoc(
    project_name="Darviq DevSecOps",
    subtitle="DevSecOps CI/CD Pipeline with Integrated Security Scanning",
    doc_kind="High-Level Design (HLD)",
    version=VERSION,
    date=DATE,
)
doc.add_document_control()
doc.add_toc_field()

# ------------------------------------------------------------------
# 1. Introduction
# ------------------------------------------------------------------
doc.add_heading1("1. Introduction")

doc.add_heading2("1.1 Purpose")
doc.add_paragraph(
    "This document describes the high-level design of Darviq DevSecOps, a reference "
    "CI/CD pipeline that implements \u201cshift-left\u201d application security. The pipeline "
    "takes a small Flask demo application as its build artifact and runs it through a "
    "sequence of static, dependency, infrastructure, container and policy security checks "
    "before the resulting container image is allowed to be pushed to a registry. The "
    "purpose of this document is to describe the architecture, components, and security "
    "controls of the pipeline at a level suitable for engineers evaluating or extending it, "
    "without going into per-file implementation detail (covered in the companion Low-Level "
    "Design document)."
)

doc.add_heading2("1.2 Scope")
doc.add_paragraph("In scope for this document:")
doc.add_bullets([
    "The GitHub Actions pipeline defined in .github/workflows/devsecops-pipeline.yaml and "
    "the companion scheduled scan in .github/workflows/scheduled-scan.yaml.",
    "The security tools actually wired into the pipeline: Bandit, Semgrep, Safety, Checkov, "
    "Trivy, Syft, and OPA (opa eval at CI time).",
    "The Kubernetes admission-control layer: the OPA/Gatekeeper ConstraintTemplates and "
    "Constraints under kubernetes/gatekeeper/, and the hardened sample Deployment they "
    "validate.",
    "The Terraform sample used as a Checkov scanning target, and the Flask demo application "
    "used as the SAST/SCA/container scanning target.",
    "The consolidated security reporting script (scripts/security-report.py).",
])
doc.add_paragraph("Out of scope for this document:")
doc.add_bullets([
    "Production operation of the Flask demo application itself \u2014 it exists purely as a "
    "scan artifact, not a real business service.",
    "Installation/operation of Gatekeeper or a Kubernetes cluster \u2014 this repository ships "
    "policy definitions but assumes a cluster with Gatekeeper already installed.",
    "Any continuous-deployment (CD) mechanism to a live cluster \u2014 as built, the pipeline "
    "stops at \u201cpush image to registry\u201d and does not apply Kubernetes manifests anywhere.",
    "Cloud provisioning of the sample S3 bucket \u2014 the Terraform is a Checkov scan target, "
    "not a Terraform pipeline with plan/apply stages.",
])

doc.add_heading2("1.3 Intended audience")
doc.add_bullets([
    "DevSecOps / platform engineers evaluating this repository as a reference implementation.",
    "Security engineers reviewing which controls are enforced versus advisory.",
    "Reviewers of the Darviq Systems portfolio assessing architecture and security design practice.",
])

doc.add_heading2("1.4 Definitions & abbreviations")
doc.add_table(
    headers=["Term", "Definition"],
    rows=[
        ["SAST", "Static Application Security Testing \u2014 analyzing source code without executing it."],
        ["SCA", "Software Composition Analysis \u2014 scanning third-party dependencies for known CVEs."],
        ["IaC", "Infrastructure as Code \u2014 infrastructure defined declaratively (here, Terraform and Kubernetes YAML)."],
        ["SBOM", "Software Bill of Materials \u2014 a machine-readable inventory of software components/packages."],
        ["SARIF", "Static Analysis Results Interchange Format \u2014 JSON format consumed by GitHub's Code Scanning UI."],
        ["OPA", "Open Policy Agent \u2014 a general-purpose policy engine using the Rego language."],
        ["Rego", "The declarative policy language used by OPA and Gatekeeper."],
        ["Gatekeeper", "A Kubernetes admission controller that enforces OPA Constraints on the live cluster."],
        ["ConstraintTemplate", "A Gatekeeper CRD that defines a reusable Rego policy and its parameter schema."],
        ["Constraint", "A Gatekeeper CRD that binds a ConstraintTemplate to specific resource kinds/namespaces."],
        ["CVE", "Common Vulnerabilities and Exposures \u2014 a public identifier for a known security vulnerability."],
        ["GHCR", "GitHub Container Registry (ghcr.io) \u2014 where the demo app's image is pushed."],
        ["Shift-left security", "Running security checks as early as possible in the development lifecycle, ideally pre-merge."],
    ],
)

# ------------------------------------------------------------------
# 2. System overview
# ------------------------------------------------------------------
doc.add_heading1("2. System overview")

doc.add_heading2("2.1 Problem statement")
doc.add_paragraph(
    "Traditional CI/CD pipelines build and deploy software with security treated as a "
    "separate, later-stage activity (a manual penetration test, a periodic audit, or a "
    "runtime firewall). By the time issues are found, the vulnerable code, dependency, "
    "container image, or Kubernetes manifest may already be running in production. "
    "Darviq DevSecOps addresses this gap by embedding automated security checks directly "
    "into the pipeline that builds the artifact, at four distinct layers \u2014 source code, "
    "third-party dependencies, infrastructure definitions, and the built container image "
    "\u2014 plus a policy layer that governs how the resulting Kubernetes workload is allowed "
    "to be configured, both at commit time (via a standalone OPA evaluation) and at "
    "deploy/admission time on a live cluster (via Gatekeeper)."
)

doc.add_heading2("2.2 Proposed solution summary")
doc.add_paragraph(
    "The repository implements a single GitHub Actions workflow (devsecops-pipeline.yaml) "
    "with seven jobs that run on every push and pull request to main/develop: SAST (Bandit "
    "+ Semgrep), SCA (Safety), IaC scanning (Checkov, against both the Terraform sample and "
    "the Kubernetes manifests), container build + image/filesystem scanning (Trivy), SBOM "
    "generation (Syft), a standalone OPA policy evaluation against the sample Deployment "
    "manifest, and a consolidated Markdown security report posted back to the pull request. "
    "A second workflow (scheduled-scan.yaml) runs a full Trivy filesystem scan every Monday "
    "to catch newly disclosed CVEs in code that hasn't changed. Separately from CI, a set of "
    "Gatekeeper ConstraintTemplates and Constraints is shipped so that, once applied to a "
    "cluster that has Gatekeeper installed, the same three policy concerns enforced by the "
    "CI-time OPA checks (no privileged containers, non-root execution, resource limits) are "
    "also enforced at admission time against anything applied directly to the cluster \u2014 "
    "not just what passed through this pipeline."
)

# ------------------------------------------------------------------
# 3. Architecture overview
# ------------------------------------------------------------------
doc.add_heading1("3. Architecture overview")

doc.add_table(
    headers=["Component", "Responsibility", "Technology"],
    rows=[
        ["CI orchestrator", "Runs the seven-job pipeline on push/PR; wires job dependencies (needs:) and artifact hand-off between jobs", "GitHub Actions (ubuntu-latest hosted runners)"],
        ["SAST stage", "Flags insecure Python coding patterns and OWASP Top-10 / secret patterns in app/", "Bandit, Semgrep"],
        ["SCA stage", "Flags known-vulnerable pinned dependencies in app/requirements.txt", "Safety"],
        ["IaC scan stage", "Scans terraform/ and kubernetes/ for misconfigurations against CIS-style benchmarks; uploads SARIF", "Checkov"],
        ["Container build & scan stage", "Builds the app image, blocks on CRITICAL CVEs, scans filesystem for secrets/misconfig, pushes to GHCR on main", "Docker Buildx, Trivy, GHCR"],
        ["SBOM stage", "Generates a component inventory of the app for supply-chain traceability", "Syft (SPDX + CycloneDX output)"],
        ["Policy check stage (CI-time)", "Evaluates the sample Deployment manifest against three standalone Rego policies", "OPA (opa eval, opa CLI)"],
        ["Admission control layer (cluster-time)", "Enforces the same three policy concerns against any workload applied to a live, Gatekeeper-enabled cluster", "OPA Gatekeeper (ConstraintTemplates + Constraints)"],
        ["Reporting stage", "Consolidates Bandit + Safety JSON output into a single Markdown summary posted as a PR comment", "Python script (scripts/security-report.py)"],
        ["Demo workload", "Minimal Flask service used purely as the artifact that flows through every scanning stage", "Flask 3.0.3, Gunicorn 22.0.0, Python 3.12"],
    ],
)

doc.add_heading2("3.1 Component descriptions")
doc.add_paragraph(
    "CI orchestrator. GitHub Actions runs each job on an ephemeral ubuntu-latest runner. "
    "Jobs sast and sca run independently and in parallel; container-scan declares "
    "needs: [sast, sca] so the image is only built after those two complete; sbom declares "
    "needs: [container-scan]; and security-report declares needs on all preceding jobs with "
    "if: always() so the summary is produced even if an earlier job failed."
)
doc.add_paragraph(
    "SAST stage. Bandit is run twice against app/: once with output suppressed (|| true) "
    "purely to always produce a bandit-report.json artifact, and a second time without "
    "suppression at --severity-level medium --confidence-level medium, which is the step "
    "that actually fails the job (and therefore the pipeline) if a medium-or-higher-severity "
    "finding exists. Semgrep is also run (p/python, p/owasp-top-ten, p/secrets rulesets) "
    "but with continue-on-error: true, making it advisory only."
)
doc.add_paragraph(
    "SCA stage. Safety checks app/requirements.txt (currently just flask and gunicorn) "
    "against its vulnerability database and writes safety-report.json, but the check runs "
    "with || true, so it never fails the build \u2014 it is purely a reporting input consumed "
    "later by scripts/security-report.py."
)
doc.add_paragraph(
    "IaC scan stage. Checkov runs twice via bridgecrewio/checkov-action: once against "
    "terraform/ (framework: terraform) and once against kubernetes/ (framework: kubernetes), "
    "both with soft_fail: true. Findings are uploaded as SARIF to GitHub's Code Scanning tab "
    "under two categories (checkov-terraform, checkov-kubernetes) rather than gating the "
    "pipeline directly."
)
doc.add_paragraph(
    "Container build & scan stage. The app/Dockerfile image is built with Docker Buildx "
    "(build only, push: false at first), tagged by docker/metadata-action with a sha-, "
    "branch-ref, and semver tag scheme. Trivy then runs three times: a CRITICAL-only scan "
    "with exit-code: 1 (the pipeline's actual container security gate), a HIGH+CRITICAL "
    "full scan uploaded as SARIF (if: always(), informational), and a filesystem scan "
    "(scan-type: fs) restricted to scanners: misconfig,secret to catch hardcoded secrets "
    "and IaC misconfigurations across the whole repo. The image is pushed to ghcr.io only "
    "if github.ref == 'refs/heads/main', meaning scans must have passed the preceding steps "
    "on that job for the push step to be reached."
)
doc.add_paragraph(
    "SBOM stage. Syft is installed via its published install script and run against app/, "
    "producing both an SPDX-JSON and a CycloneDX-JSON SBOM, uploaded as workflow artifacts."
)
doc.add_paragraph(
    "Policy check stage (CI-time). The opa CLI is downloaded directly from "
    "openpolicyagent.org and run three times, once per Rego file in opa/policies/ "
    "(deny-privileged.rego, require-labels.rego, resource-limits.rego), each evaluated "
    "with opa eval --data <file> --input kubernetes/deployment.yaml \"data.kubernetes.deny\". "
    "As written, these opa eval invocations do not pass --fail-defined, so the step's exit "
    "code is 0 regardless of whether the deny set is non-empty \u2014 today this stage prints "
    "policy violations to the job log but does not itself fail the pipeline. This is called "
    "out again in the Security design and Assumptions sections below."
)
doc.add_paragraph(
    "Admission control layer. Independently of CI, kubernetes/gatekeeper/constraint-templates/ "
    "defines three Gatekeeper ConstraintTemplates (K8sBlockPrivileged, K8sRequireNonRoot, "
    "K8sRequireResourceLimits) and kubernetes/gatekeeper/constraints/ binds each to a matching "
    "Constraint with enforcementAction: deny, scoped to Deployment (and, for two of the three, "
    "DaemonSet/StatefulSet) resources, excluding kube-system (and monitoring for the non-root "
    "constraint). These take effect only once kubectl-applied to a cluster that already has "
    "Gatekeeper installed \u2014 no pipeline job applies them automatically."
)
doc.add_paragraph(
    "Reporting stage. scripts/security-report.py parses bandit-report.json and "
    "safety-report.json (downloaded from the earlier jobs' artifacts), buckets findings by "
    "severity, and writes security-summary.md, which is posted as a PR comment via "
    "actions/github-script when the workflow was triggered by a pull_request event. Checkov "
    "and Trivy findings are not currently parsed by this script \u2014 they remain visible only "
    "in the GitHub Security / Code Scanning tab via their SARIF uploads."
)

# ------------------------------------------------------------------
# 4. End-to-end functional workflow
# ------------------------------------------------------------------
doc.add_heading1("4. End-to-end functional workflow")
doc.add_figure_placeholder(
    "Figure 4.1 \u2014 Pipeline flow: commit/PR -> parallel SAST/SCA/IaC scan -> "
    "container build & Trivy gate -> SBOM -> OPA policy check -> consolidated report -> "
    "(main only) image push to GHCR -> (out of pipeline) manual apply to Gatekeeper-enabled cluster"
)
doc.add_paragraph(
    "A developer pushes a commit or opens a pull request against main or develop. GitHub "
    "Actions triggers devsecops-pipeline.yaml. The sast, sca, and iac-scan jobs start "
    "immediately and run in parallel since none depends on another. Once both sast and sca "
    "complete, container-scan builds the Docker image, runs the blocking CRITICAL-only "
    "Trivy scan, and \u2014 only if that step exits 0 \u2014 proceeds to the filesystem scan and, on "
    "main only, pushes the image to GHCR. sbom then generates the SBOM from the built image "
    "context. Independently, opa-check evaluates the repository's sample "
    "kubernetes/deployment.yaml against the three standalone Rego policies and prints any "
    "violations to the log. Finally, security-report runs after all preceding jobs "
    "(if: always()) to guarantee it executes even on failure, downloads the Bandit and "
    "Safety artifacts, generates security-summary.md, and \u2014 for pull_request events \u2014 posts "
    "it as a PR comment. The pipeline's job stops there: nothing in this repository applies "
    "the resulting image or its Kubernetes manifests to a live cluster. If a cluster operator "
    "later runs kubectl apply -f kubernetes/deployment.yaml against a Gatekeeper-enabled "
    "cluster carrying this repo's Constraints, the same privileged/root/resource-limit rules "
    "are re-checked a second time at admission, independent of whatever happened in CI."
)

doc.add_table(
    headers=["Stage (job name)", "Trigger condition", "Outcome if it fails / finds issues"],
    rows=[
        ["sast", "Every push/PR to main or develop", "Job fails on Bandit medium+ finding (second, unsuppressed run); Semgrep findings are advisory only"],
        ["sca", "Every push/PR to main or develop", "Never fails the job (|| true); findings feed the PR report only"],
        ["iac-scan", "Every push/PR to main or develop", "Never fails the job (soft_fail: true); findings appear as SARIF in the Security tab"],
        ["container-scan", "After sast + sca succeed", "Fails on any CRITICAL image CVE (exit-code: 1); HIGH+CRITICAL and fs findings are reported, not blocking"],
        ["sbom", "After container-scan", "No pass/fail condition \u2014 pure artifact generation"],
        ["opa-check", "Every push/PR to main or develop", "Prints deny messages to the log but does not fail the job as currently written (no --fail-defined)"],
        ["security-report", "After all jobs, always (if: always())", "No pass/fail condition \u2014 posts a PR comment summarizing Bandit/Safety findings"],
        ["full-scan (scheduled-scan.yaml)", "Weekly, Monday 02:00 UTC, or manual workflow_dispatch", "Uploads a MEDIUM/HIGH/CRITICAL SARIF report; does not fail the run"],
    ],
)

# ------------------------------------------------------------------
# 5. Module-wise design overview
# ------------------------------------------------------------------
doc.add_heading1("5. Module-wise design overview")

doc.add_heading2("5.1 Static Application Security Testing (SAST)")
doc.add_paragraph(
    "Bandit scans app/ for insecure Python patterns (e.g. use of eval, weak hashing, "
    "hardcoded binds) at medium severity/confidence; it is the pipeline's actual SAST gate. "
    "Semgrep supplements it with the p/python, p/owasp-top-ten, and p/secrets community "
    "rulesets, but runs as an advisory step (continue-on-error: true) rather than a gate."
)

doc.add_heading2("5.2 Software Composition Analysis (SCA)")
doc.add_paragraph(
    "Safety checks the two pinned dependencies in app/requirements.txt (flask, gunicorn) "
    "against its vulnerability feed and writes a JSON report. It runs in report-only mode "
    "(|| true) and does not currently gate the build."
)

doc.add_heading2("5.3 Infrastructure-as-Code (IaC) scanning")
doc.add_paragraph(
    "Checkov scans the Terraform sample (terraform/main.tf, a hardened S3 bucket) and the "
    "Kubernetes manifests (kubernetes/), producing SARIF uploaded to two separate Code "
    "Scanning categories. It runs in soft-fail mode, so findings surface for triage rather "
    "than blocking merges."
)

doc.add_heading2("5.4 Container image & filesystem scanning")
doc.add_paragraph(
    "Trivy performs three distinct scans against the built application image and the repo "
    "filesystem: a blocking CRITICAL-CVE image scan, an informational HIGH+CRITICAL SARIF "
    "image scan, and a filesystem scan restricted to secret and misconfiguration detectors. "
    "It is the only tool in the pipeline configured to hard-fail the job on its own findings."
)

doc.add_heading2("5.5 Software Bill of Materials (SBOM)")
doc.add_paragraph(
    "Syft generates an SPDX-JSON and a CycloneDX-JSON SBOM for the app/ directory, uploaded "
    "as workflow artifacts for supply-chain traceability. No downstream consumer currently "
    "diffs or validates these SBOMs; they are produced for audit/record purposes."
)

doc.add_heading2("5.6 Policy-as-code validation (CI-time, OPA)")
doc.add_paragraph(
    "Three standalone Rego files under opa/policies/ (package kubernetes) are evaluated "
    "against kubernetes/deployment.yaml using the opa CLI's opa eval command: "
    "deny-privileged.rego (blocks privileged containers, hostPID, hostNetwork), "
    "require-labels.rego (requires app/version/team/env labels on both the Deployment and "
    "its pod template), and resource-limits.rego (requires CPU/memory limits and a CPU "
    "request). This is a design-time check meant to catch policy drift before a manifest is "
    "ever applied to a cluster."
)

doc.add_heading2("5.7 Kubernetes admission control (Gatekeeper)")
doc.add_paragraph(
    "Three Gatekeeper ConstraintTemplate/Constraint pairs mirror the CI-time OPA checks at "
    "the cluster level: K8sBlockPrivileged, K8sRequireNonRoot (not covered by a standalone "
    "opa/policies/ file \u2014 this is a Gatekeeper-only check), and K8sRequireResourceLimits. "
    "Enforcement is enforcementAction: deny for all three, meaning a non-compliant "
    "create/update request is rejected by the API server at admission time, independent of "
    "whether it originated from this pipeline."
)

doc.add_heading2("5.8 Consolidated security reporting")
doc.add_paragraph(
    "scripts/security-report.py reads bandit-report.json and safety-report.json, groups "
    "findings by CRITICAL/HIGH/MEDIUM severity, and renders a Markdown table plus itemized "
    "critical/high findings, posted as a PR comment. It intentionally keeps a narrow scope "
    "(two tools) rather than re-deriving what SARIF/Code-Scanning already surfaces for "
    "Checkov and Trivy."
)

# ------------------------------------------------------------------
# 6. Data design (Configuration & policy model)
# ------------------------------------------------------------------
doc.add_heading1("6. Configuration & policy model")
doc.add_paragraph(
    "This repository has no application data model \u2014 the Flask demo app is stateless "
    "(three JSON endpoints, no database). What plays the equivalent role of a \u201cdata design\u201d "
    "here is the configuration and policy model: the set of declarative files that define "
    "what is scanned, how strictly, and what a compliant Kubernetes workload must look like."
)
doc.add_table(
    headers=["Configuration artifact", "Defines"],
    rows=[
        ["opa/policies/*.rego", "Three standalone Rego policies (package kubernetes) evaluated at CI time against a single sample manifest"],
        ["kubernetes/gatekeeper/constraint-templates/*.yaml", "The reusable Rego logic + CRD schema for each cluster-enforced policy (privileged, non-root, resource limits)"],
        ["kubernetes/gatekeeper/constraints/*.yaml", "Which resource kinds/namespaces each ConstraintTemplate applies to, and its enforcementAction"],
        ["kubernetes/deployment.yaml", "The single hardened reference Deployment used as both the OPA CI input and the manifest a cluster operator would apply"],
        ["terraform/main.tf", "The single Checkov scan target for IaC \u2014 an intentionally hardened S3 bucket (versioning, KMS SSE, public-access block, access logging)"],
        [".github/workflows/*.yaml", "The pipeline's own configuration: job graph, triggers, severity thresholds, and which steps are blocking vs. advisory"],
        ["app/requirements.txt", "The dependency set Safety checks (currently two pinned packages)"],
    ],
)

# ------------------------------------------------------------------
# 7. Technology stack
# ------------------------------------------------------------------
doc.add_heading1("7. Technology stack")
doc.add_table(
    headers=["Layer", "Technology", "Notes"],
    rows=[
        ["CI/CD orchestration", "GitHub Actions (ubuntu-latest)", "Two workflows: push/PR pipeline and a weekly scheduled full scan"],
        ["Demo application", "Python 3.12, Flask 3.0.3, Gunicorn 22.0.0", "Minimal service (/, /health, /ready) used purely as a scan artifact"],
        ["Containerization", "Docker, Docker Buildx", "Non-root image (UID/GID 10001), GHA layer caching (type=gha)"],
        ["Container registry", "GHCR (ghcr.io)", "Pushed only from main, after the blocking Trivy step passes"],
        ["SAST", "Bandit, Semgrep", "Bandit gates the build; Semgrep is advisory (continue-on-error)"],
        ["SCA", "Safety", "Report-only (|| true) against app/requirements.txt"],
        ["IaC scanning", "Checkov (bridgecrewio/checkov-action)", "SARIF output, soft_fail: true, against terraform/ and kubernetes/"],
        ["Container/FS scanning", "Trivy (aquasecurity/trivy-action)", "CRITICAL image scan is the one hard gate; HIGH+CRITICAL + fs scans are SARIF/informational"],
        ["SBOM generation", "Syft (anchore)", "SPDX-JSON and CycloneDX-JSON outputs, uploaded as artifacts"],
        ["Policy as code (CI)", "OPA / Rego (opa CLI)", "opa eval against opa/policies/*.rego, currently non-blocking"],
        ["Policy as code (cluster)", "OPA Gatekeeper", "ConstraintTemplates + Constraints, enforcementAction: deny"],
        ["IaC sample", "Terraform ~1.x, hashicorp/aws ~> 5.0", "Single hardened S3 bucket, no plan/apply stage in CI"],
        ["Reporting", "Python 3.12, rich", "scripts/security-report.py \u2192 security-summary.md, posted via actions/github-script"],
    ],
)

# ------------------------------------------------------------------
# 8. Deployment architecture
# ------------------------------------------------------------------
doc.add_heading1("8. Deployment architecture")
doc.add_figure_placeholder(
    "Figure 8.1 \u2014 GitHub-hosted runners execute all jobs; the built image lands in GHCR; "
    "Kubernetes manifests and Gatekeeper policy CRDs are separate artifacts applied manually "
    "to a cluster that has Gatekeeper pre-installed"
)
doc.add_paragraph(
    "There is no dedicated infrastructure for this pipeline to operate \u2014 every job runs on "
    "an ephemeral, GitHub-hosted ubuntu-latest runner, and tools such as OPA and Syft are "
    "downloaded fresh (via curl, unpinned to a specific release/checksum) at the start of "
    "each run rather than pre-baked into a custom runner image. The only persistent output "
    "of the pipeline is the container image pushed to ghcr.io/ravishekharg/devsecops-pipeline/"
    "devsecops-app, tagged by commit SHA, branch, and semver, plus the SARIF/artifact "
    "records retained by GitHub (Code Scanning alerts, SBOM files, Bandit/Safety JSON). "
    "The Kubernetes side is deliberately decoupled from CI: kubernetes/deployment.yaml and "
    "the kubernetes/gatekeeper/ ConstraintTemplates and Constraints are reference manifests "
    "that a cluster operator applies out-of-band with kubectl, to a cluster where Gatekeeper "
    "has already been installed (a stated prerequisite, not something this repo automates). "
    "Once applied, Gatekeeper's admission webhook re-evaluates the same three policy concerns "
    "(privileged, non-root, resource limits) on every create/update to a matching workload, "
    "regardless of whether that workload ever passed through this repository's CI pipeline."
)
doc.add_table(
    headers=["Variable / setting", "Where used", "Purpose"],
    rows=[
        ["IMAGE_NAME", "devsecops-pipeline.yaml env", "Base name for the built image (devsecops-app)"],
        ["REGISTRY", "devsecops-pipeline.yaml env", "Target registry host (ghcr.io)"],
        ["permissions.packages: write", "devsecops-pipeline.yaml", "Grants the job token push access to GHCR"],
        ["permissions.security-events: write", "both workflows", "Grants SARIF-upload access to GitHub Code Scanning"],
        ["GITHUB_TOKEN (implicit secret)", "docker/login-action, github-script", "Authenticates to GHCR and to the GitHub API for PR comments"],
        ["APP_VERSION", "app/app.py (os.getenv)", "Runtime-only display value returned by the / endpoint; defaults to 1.0.0"],
        ["cron: '0 2 * * 1'", "scheduled-scan.yaml", "Fires the weekly full filesystem scan every Monday 02:00 UTC"],
    ],
)

# ------------------------------------------------------------------
# 9. Security design
# ------------------------------------------------------------------
doc.add_heading1("9. Security design")
doc.add_paragraph(
    "The pipeline implements defense-in-depth across five layers, but it is important to be "
    "precise about which layers actually block a build/merge today versus which are "
    "advisory/reporting-only, since that distinction is the pipeline's real current security "
    "posture, not an idealized one."
)
doc.add_table(
    headers=["Layer", "Tool / mechanism", "Enforcement today"],
    rows=[
        ["Code", "Bandit (medium+ severity/confidence)", "Blocking \u2014 fails the sast job"],
        ["Code (secondary)", "Semgrep (python/owasp-top-ten/secrets)", "Advisory \u2014 continue-on-error: true"],
        ["Dependencies", "Safety", "Advisory \u2014 runs with || true"],
        ["Infrastructure (Terraform + K8s YAML)", "Checkov", "Advisory \u2014 soft_fail: true, surfaced via SARIF"],
        ["Container image", "Trivy CRITICAL scan", "Blocking \u2014 exit-code: 1 on any CRITICAL CVE"],
        ["Container image (full)", "Trivy HIGH+CRITICAL scan", "Advisory \u2014 SARIF upload, if: always()"],
        ["Filesystem / secrets", "Trivy fs scan (misconfig, secret)", "Advisory \u2014 SARIF upload, not gated"],
        ["Manifest (design-time)", "OPA (opa eval, three Rego policies)", "Currently non-blocking \u2014 no --fail-defined flag, so the step exits 0 regardless of deny results"],
        ["Manifest (admission-time)", "Gatekeeper (three Constraints, enforcementAction: deny)", "Blocking, but only on clusters where these Constraints have been applied \u2014 not invoked by CI at all"],
    ],
)
doc.add_paragraph(
    "The three Gatekeeper policies enforced at admission time are: (1) K8sBlockPrivileged, "
    "which denies any Deployment/DaemonSet/StatefulSet container with "
    "securityContext.privileged == true; (2) K8sRequireNonRoot, which denies a container "
    "unless securityContext.runAsNonRoot is set and additionally denies "
    "securityContext.runAsUser == 0; and (3) K8sRequireResourceLimits, which denies a "
    "container missing resources.limits.cpu, resources.limits.memory, or "
    "resources.requests.cpu. All three exclude kube-system from enforcement, and "
    "K8sRequireNonRoot additionally excludes monitoring. The bundled "
    "kubernetes/deployment.yaml sample is deliberately hardened (runAsNonRoot: true, "
    "runAsUser: 10001, allowPrivilegeEscalation: false, capabilities.drop: [ALL], "
    "readOnlyRootFilesystem: true, explicit CPU/memory requests and limits, "
    "automountServiceAccountToken: false, seccompProfile: RuntimeDefault) specifically so "
    "that it passes both the CI-time OPA checks and the cluster-time Gatekeeper Constraints, "
    "demonstrating the intended compliant end state rather than a violation case."
)
doc.add_paragraph(
    "Supply-chain visibility is handled separately from the blocking/advisory gates above: "
    "Syft's SPDX and CycloneDX SBOMs give a point-in-time component inventory of the app "
    "image, and the weekly scheduled-scan.yaml re-runs a broader Trivy filesystem scan "
    "(MEDIUM/HIGH/CRITICAL) so that CVEs disclosed after a commit was last scanned are still "
    "caught even without new code changes."
)

# ------------------------------------------------------------------
# 10. Non-functional requirements
# ------------------------------------------------------------------
doc.add_heading1("10. Non-functional requirements")
doc.add_table(
    headers=["Attribute", "Target / approach"],
    rows=[
        ["Pipeline latency", "sast, sca, and iac-scan run in parallel with no interdependency, keeping wall-clock time close to the slowest single job rather than the sum of all jobs; no explicit SLA is enforced in the workflow itself"],
        ["False-positive handling", "Checkov, Safety, the full Trivy scan, and the fs scan all run in non-blocking modes (soft_fail, || true, if: always()) precisely so noisy or debatable findings surface for human triage in the Security tab/PR comment rather than blocking every merge"],
        ["Signal-to-noise on hard gates", "Only two checks hard-fail a job today: Bandit at medium+ severity/confidence, and Trivy at CRITICAL image CVEs \u2014 a deliberately narrow, high-confidence blocking set"],
        ["Auditability", "SARIF uploads (two Checkov categories + Trivy image) feed GitHub's native Code Scanning UI; SBOMs and Bandit/Safety JSON are retained as workflow artifacts"],
        ["Repeatability / drift detection", "The weekly scheduled-scan.yaml re-scans the filesystem independent of code changes, catching newly disclosed CVEs in unchanged dependencies"],
        ["Runner scalability", "Stateless, ephemeral GitHub-hosted runners; each workflow run is independent, with no shared mutable state beyond upload/download-artifact hand-offs"],
        ["Tooling reproducibility", "OPA and Syft are installed by curl-ing latest at run time rather than pinned to a version/checksum, which is a trade-off in favor of simplicity over strict reproducibility"],
    ],
)

# ------------------------------------------------------------------
# 11. Assumptions & constraints
# ------------------------------------------------------------------
doc.add_heading1("11. Assumptions & constraints")
doc.add_bullets([
    "Assumes GitHub-hosted runners with outbound internet access, since OPA, Syft, and several "
    "actions download binaries/rulesets at run time rather than from a pinned/cached source.",
    "Assumes the target Kubernetes cluster already has Gatekeeper installed; this repository "
    "supplies only the ConstraintTemplate/Constraint CRs, not Gatekeeper itself.",
    "Assumes the repository's GITHUB_TOKEN has packages: write scope so the container-scan job "
    "can push to GHCR; this depends on repository/organization package settings.",
    "The Terraform sample has no backend configuration, plan step, or apply step in CI \u2014 it "
    "exists solely as a Checkov scan target, not as a provisioning pipeline.",
    "There is exactly one demo microservice and one sample Deployment manifest; the pipeline "
    "is not demonstrated at multi-service fan-out scale.",
    "As currently coded, the opa-check job does not fail the pipeline on policy violations "
    "(no --fail-defined on opa eval) \u2014 the README's \"Security Gates\" list describes OPA/"
    "Gatekeeper as blocking deployment, which is accurate for the Gatekeeper admission-control "
    "layer on a live cluster, but the CI-time OPA step as implemented is currently advisory.",
    "scripts/security-report.py aggregates only Bandit and Safety output; Checkov and Trivy "
    "findings are visible only via their SARIF uploads in the GitHub Security tab, not in the "
    "PR comment.",
    "No continuous-deployment mechanism exists in this repository \u2014 pushing an image to GHCR "
    "is the pipeline's final step; applying manifests to a cluster is a manual, out-of-band "
    "operation.",
])

# ------------------------------------------------------------------
# 12. Future enhancements
# ------------------------------------------------------------------
doc.add_heading1("12. Future enhancements")
doc.add_bullets([
    "Add --fail-defined (or an equivalent conftest-style wrapper) to the opa-check job so a "
    "non-empty deny set actually fails the pipeline, matching the blocking behavior already "
    "implied by the README's Security Gates section.",
    "Extend scripts/security-report.py to also parse the Checkov and Trivy SARIF outputs, so "
    "the PR comment becomes a single consolidated view of all five scanners instead of two.",
    "Add a real CD stage \u2014 e.g. a GitOps-style manifest push, or a server-side dry-run "
    "(kubectl apply --dry-run=server) against a staging cluster \u2014 to close the loop between "
    "a passing pipeline and an actually-deployed, Gatekeeper-checked workload.",
    "Pin the OPA and Syft install steps to specific released versions with checksum "
    "verification instead of curl-ing latest on every run.",
    "Add a dedicated secrets-scanning tool (e.g. gitleaks or truffleHog) as a defense-in-depth "
    "companion to Trivy's built-in fs secret scanner.",
    "Expand the Terraform sample with an intentionally non-compliant resource (or a second "
    "module) so Checkov's failure path and SARIF output can be exercised in addition to its "
    "clean-pass path.",
])

# ------------------------------------------------------------------
# 13. Appendix
# ------------------------------------------------------------------
doc.add_heading1("13. Appendix")

doc.add_heading2("13.1 References")
doc.add_bullets([
    "Repository README.md (pipeline stages, security gates, quick-start commands)",
    ".github/workflows/devsecops-pipeline.yaml \u2014 primary CI pipeline",
    ".github/workflows/scheduled-scan.yaml \u2014 weekly full scan",
    "opa/policies/*.rego \u2014 CI-time OPA policies",
    "kubernetes/gatekeeper/ \u2014 ConstraintTemplates and Constraints",
    "Open Policy Agent documentation: https://www.openpolicyagent.org/docs/latest/",
    "OPA Gatekeeper documentation: https://open-policy-agent.github.io/gatekeeper/",
    "Aqua Trivy documentation: https://aquasecurity.github.io/trivy/",
    "Anchore Syft: https://github.com/anchore/syft",
    "Bridgecrew Checkov: https://www.checkov.io/",
])

doc.add_heading2("13.2 Change history")
doc.add_table(
    headers=["Version", "Date", "Description"],
    rows=[
        ["1.0", DATE, "Initial high-level design document"],
    ],
)

doc.save("D:/Projects/DevOps/Darviq-DevSecOps/Docs/Darviq_DevSecOps_High_Level_Design.docx")
print("HLD saved.")
