# -*- coding: utf-8 -*-
"""Generates Darviq_DevSecOps_Low_Level_Design.docx from the docx_builder helper."""
from docx_builder import DesignDoc

VERSION = "1.0"
DATE = "July 31, 2026"

doc = DesignDoc(
    project_name="Darviq DevSecOps",
    subtitle="DevSecOps CI/CD Pipeline with Integrated Security Scanning",
    doc_kind="Low-Level Design (LLD)",
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
    "This Low-Level Design document expands on the Darviq DevSecOps High-Level Design "
    "(Darviq_DevSecOps_High_Level_Design.docx) with file-level, tool-invocation-level, and "
    "policy-rule-level detail. Where the HLD describes eight logical modules (SAST, SCA, IaC "
    "scanning, container/filesystem scanning, SBOM, CI-time OPA policy, cluster-time "
    "Gatekeeper admission control, and consolidated reporting), this document cites the "
    "actual files, job/step names, tool flags, and Rego rule bodies that implement each one, "
    "so an engineer can locate and modify the exact code responsible for any given control."
)

doc.add_heading2("1.2 Scope")
doc.add_paragraph(
    "This document covers implementation-level detail for every job in "
    ".github/workflows/devsecops-pipeline.yaml and .github/workflows/scheduled-scan.yaml, "
    "every Rego file under opa/policies/ and kubernetes/gatekeeper/, the sample "
    "kubernetes/deployment.yaml and terraform/main.tf, the Flask demo application under "
    "app/, and scripts/security-report.py. It does not re-derive the architectural rationale "
    "already covered in the HLD."
)

doc.add_heading2("1.3 References")
doc.add_bullets([
    "Darviq_DevSecOps_High_Level_Design.docx (this document's companion HLD)",
    ".github/workflows/devsecops-pipeline.yaml",
    ".github/workflows/scheduled-scan.yaml",
    "opa/policies/deny-privileged.rego, require-labels.rego, resource-limits.rego",
    "kubernetes/gatekeeper/constraint-templates/*.yaml, kubernetes/gatekeeper/constraints/*.yaml",
    "kubernetes/deployment.yaml",
    "terraform/main.tf",
    "app/app.py, app/Dockerfile, app/requirements.txt",
    "scripts/security-report.py",
])

# ------------------------------------------------------------------
# 2. Detailed module design
# ------------------------------------------------------------------
doc.add_heading1("2. Detailed module design")

doc.add_heading2("2.1 Static Application Security Testing (SAST)")
doc.add_paragraph("Job: sast in devsecops-pipeline.yaml. Runs on ubuntu-latest with Python 3.12 set up via actions/setup-python@v5.")
doc.add_bullets([
    "pip install bandit[toml] installs Bandit.",
    "Step 1: bandit -r app/ -f json -o bandit-report.json --severity-level medium "
    "--confidence-level medium || true \u2014 always succeeds (|| true) so the JSON artifact is "
    "always produced, even when findings exist.",
    "Step 2: bandit -r app/ --severity-level medium --confidence-level medium (no suppression) "
    "\u2014 this is the real gate; a medium-or-higher severity+confidence finding gives Bandit a "
    "non-zero exit code and fails the sast job, which cascades to block container-scan "
    "(needs: [sast, sca]).",
    "returntocorp/semgrep-action@v1 runs with config: p/python p/owasp-top-ten p/secrets and "
    "continue-on-error: true, so its findings never fail the job regardless of severity.",
    "bandit-report.json is uploaded via actions/upload-artifact@v4 under the name "
    "bandit-report, later downloaded by the security-report job.",
])

doc.add_heading2("2.2 Software Composition Analysis (SCA)")
doc.add_paragraph("Job: sca in devsecops-pipeline.yaml.")
doc.add_bullets([
    "pip install safety, then pip install -r app/requirements.txt (installs flask==3.0.3, "
    "gunicorn==22.0.0 so Safety can resolve exact installed versions).",
    "safety check --full-report --json --output safety-report.json || true \u2014 always exits 0, "
    "so this stage never blocks the pipeline regardless of CVE severity found.",
    "safety-report.json uploaded as artifact safety-report, later downloaded by "
    "security-report.",
])

doc.add_heading2("2.3 Infrastructure-as-Code (IaC) scanning")
doc.add_paragraph("Job: iac-scan in devsecops-pipeline.yaml.")
doc.add_bullets([
    "bridgecrewio/checkov-action@master run #1: directory: terraform/, framework: terraform, "
    "output_format: sarif, output_file_path: checkov-terraform.sarif, soft_fail: true.",
    "bridgecrewio/checkov-action@master run #2: directory: kubernetes/, framework: kubernetes, "
    "output_format: sarif, output_file_path: checkov-k8s.sarif, soft_fail: true.",
    "Both SARIF files are uploaded via github/codeql-action/upload-sarif@v3 under categories "
    "checkov-terraform and checkov-kubernetes respectively, surfacing findings in the repo's "
    "Security > Code scanning tab rather than in the job's pass/fail status.",
])

doc.add_heading2("2.4 Container image & filesystem scanning")
doc.add_paragraph("Job: container-scan (needs: [sast, sca]) in devsecops-pipeline.yaml.")
doc.add_bullets([
    "docker/setup-buildx-action@v3 and docker/login-action@v3 (against ghcr.io, using "
    "github.actor / secrets.GITHUB_TOKEN) prepare the build.",
    "docker/metadata-action@v5 computes tags for "
    "${REGISTRY}/${{github.repository}}/${IMAGE_NAME}: sha-<sha>, the branch ref, and a "
    "semver tag pattern.",
    "docker/build-push-action@v5 (id: build) builds app/ (context: app/, using app/Dockerfile "
    "implicitly) with push: false, load: true, and GHA layer caching (cache-from/cache-to: "
    "type=gha).",
    "aquasecurity/trivy-action@master run #1 (the hard gate): image-ref: <built tags>, "
    "format: table, exit-code: \"1\", severity: CRITICAL, vuln-type: os,library \u2014 fails the "
    "job on any CRITICAL OS/library CVE in the built image.",
    "aquasecurity/trivy-action@master run #2 (if: always()): format: sarif, output: "
    "trivy-image.sarif, severity: HIGH,CRITICAL \u2014 broader, informational scan uploaded via "
    "github/codeql-action/upload-sarif@v3 under category trivy-image.",
    "aquasecurity/trivy-action@master run #3: scan-type: fs, scan-ref: ., format: sarif, "
    "output: trivy-fs.sarif, scanners: misconfig,secret \u2014 scans the whole checked-out "
    "repository (not just the image) for hardcoded secrets and IaC misconfigurations. Note: "
    "this SARIF is produced but has no corresponding upload-sarif step in the workflow as "
    "written, so trivy-fs.sarif is generated but not currently surfaced in the Security tab.",
    "docker/build-push-action@v5 (final step): push: ${{ github.ref == 'refs/heads/main' }} "
    "\u2014 only pushes to GHCR on main, and only if every preceding step in this job (including "
    "the blocking CRITICAL Trivy scan) succeeded.",
])

doc.add_heading2("2.5 Software Bill of Materials (SBOM)")
doc.add_paragraph("Job: sbom (needs: [container-scan]) in devsecops-pipeline.yaml.")
doc.add_bullets([
    "Installs Syft via curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/"
    "install.sh | sh -s -- -b /usr/local/bin (unpinned to a release tag).",
    "syft app/ --output spdx-json=sbom-spdx.json --output cyclonedx-json="
    "sbom-cyclonedx.json --output table \u2014 scans the app/ source directory (not the built "
    "image) and emits two machine-readable SBOM formats plus a human-readable table.",
    "Both JSON files are uploaded via actions/upload-artifact@v4 under the name sbom.",
])

doc.add_heading2("2.6 Policy-as-code validation (CI-time, OPA)")
doc.add_paragraph("Job: opa-check in devsecops-pipeline.yaml.")
doc.add_bullets([
    "Installs the opa CLI via curl -L -o opa https://openpolicyagent.org/downloads/latest/"
    "opa_linux_amd64_static, chmod +x opa, sudo mv opa /usr/local/bin/ (unpinned to a "
    "specific OPA version).",
    "Runs three separate opa eval invocations, each scoped to a single Rego file, all against "
    "the same input: kubernetes/deployment.yaml, and all querying \"data.kubernetes.deny\":",
    "  1) --data opa/policies/deny-privileged.rego",
    "  2) --data opa/policies/require-labels.rego",
    "  3) --data opa/policies/resource-limits.rego",
    "Each uses --format pretty, which prints the deny set (empty array if compliant) to the "
    "job log. None of the three invocations passes --fail-defined or --fail, so opa eval's "
    "own exit code is 0 whenever the Rego evaluates without a runtime/compile error \u2014 a "
    "non-empty deny array does NOT fail the step or the job as currently written.",
])

doc.add_heading2("2.7 Kubernetes admission control (Gatekeeper)")
doc.add_paragraph(
    "Not a CI job \u2014 this is a set of static manifests under kubernetes/gatekeeper/ that a "
    "cluster operator applies manually (kubectl apply -f ...) to a cluster that already has "
    "Gatekeeper installed. See Section 3 below for the full ConstraintTemplate/Constraint "
    "reference."
)

doc.add_heading2("2.8 Consolidated security reporting")
doc.add_paragraph("Job: security-report (needs: [sast, sca, iac-scan, container-scan, sbom, opa-check], if: always()).")
doc.add_bullets([
    "actions/download-artifact@v4 (no name filter) pulls down all artifacts from earlier jobs "
    "into the workspace, including bandit-report/bandit-report.json and safety-report/"
    "safety-report.json.",
    "pip install rich, then python scripts/security-report.py.",
    "Inside security-report.py: parse_bandit() reads bandit-report/bandit-report.json and "
    "maps each result to a Finding(tool=\"Bandit (SAST)\", severity=issue_severity, "
    "title=issue_text, location=\"<filename>:<line_number>\"); parse_safety() reads "
    "safety-report/safety-report.json and maps each vulnerability to a Finding(tool="
    "\"Safety (SCA)\", severity=severity.upper(), title=advisory, location=\"<package> "
    "<version>\", cve=CVE).",
    "generate_markdown() buckets findings into CRITICAL/HIGH/MEDIUM, renders a severity-count "
    "table plus itemized Critical/High sections, and sets a pass/fail emoji purely from "
    "whether any Critical or High findings exist (this is a cosmetic status indicator in the "
    "report text, not a build gate \u2014 it does not affect the job's actual exit code).",
    "The rendered security-summary.md is written to disk, then posted as a PR comment via "
    "actions/github-script@v7, but only if: github.event_name == 'pull_request'.",
    "Checkov (checkov-terraform.sarif / checkov-k8s.sarif) and Trivy (trivy-image.sarif / "
    "trivy-fs.sarif) results are never read by this script \u2014 they are visible only through "
    "their SARIF uploads to the GitHub Security tab, not in the PR comment body.",
])

# ------------------------------------------------------------------
# 3. Policy reference: Gatekeeper ConstraintTemplates & Constraints
# ------------------------------------------------------------------
doc.add_heading1("3. Policy reference: Gatekeeper ConstraintTemplates & Constraints")
doc.add_paragraph(
    "This section replaces the traditional \u201cdatabase schema design\u201d section, since this "
    "repository's persistent, structured \u201cschema\u201d is its set of enforceable Kubernetes "
    "admission policies rather than a data store. Each ConstraintTemplate defines the Rego "
    "violation logic and CRD kind; each Constraint binds that template to specific resource "
    "kinds/namespaces with an enforcementAction."
)

doc.add_heading2("3.1 K8sBlockPrivileged")
doc.add_paragraph("File: kubernetes/gatekeeper/constraint-templates/block-privileged.yaml")
doc.add_code_block(
    'package k8sblockprivileged\n\n'
    'violation[{"msg": msg}] if {\n'
    '    container := input.review.object.spec.template.spec.containers[_]\n'
    '    container.securityContext.privileged == true\n'
    '    msg := sprintf(\n'
    '        "Container \'%v\' must not run in privileged mode",\n'
    '        [container.name]\n'
    '    )\n'
    '}'
)
doc.add_paragraph("Constraint (kubernetes/gatekeeper/constraints/block-privileged.yaml): kind K8sBlockPrivileged, name block-privileged.")
doc.add_table(
    headers=["Parameter", "Value"],
    rows=[
        ["match.kinds", "apiGroups: [apps], kinds: [Deployment, DaemonSet, StatefulSet]"],
        ["match.excludedNamespaces", "kube-system"],
        ["enforcementAction", "deny"],
    ],
)

doc.add_heading2("3.2 K8sRequireNonRoot")
doc.add_paragraph("File: kubernetes/gatekeeper/constraint-templates/require-non-root.yaml")
doc.add_code_block(
    'package k8srequirenonroot\n\n'
    'violation[{"msg": msg}] if {\n'
    '    container := input.review.object.spec.template.spec.containers[_]\n'
    '    not container.securityContext.runAsNonRoot\n'
    '    msg := sprintf(\n'
    '        "Container \'%v\' must set runAsNonRoot: true",\n'
    '        [container.name]\n'
    '    )\n'
    '}\n\n'
    'violation[{"msg": msg}] if {\n'
    '    container := input.review.object.spec.template.spec.containers[_]\n'
    '    container.securityContext.runAsUser == 0\n'
    '    msg := sprintf(\n'
    '        "Container \'%v\' must not run as UID 0 (root)",\n'
    '        [container.name]\n'
    '    )\n'
    '}'
)
doc.add_paragraph("Constraint (kubernetes/gatekeeper/constraints/require-non-root.yaml): kind K8sRequireNonRoot, name require-non-root.")
doc.add_table(
    headers=["Parameter", "Value"],
    rows=[
        ["match.kinds", "apiGroups: [apps], kinds: [Deployment]"],
        ["match.excludedNamespaces", "kube-system, monitoring"],
        ["enforcementAction", "deny"],
    ],
)

doc.add_heading2("3.3 K8sRequireResourceLimits")
doc.add_paragraph("File: kubernetes/gatekeeper/constraint-templates/require-resource-limits.yaml")
doc.add_code_block(
    'package k8srequireresourcelimits\n\n'
    'violation[{"msg": msg}] if {\n'
    '    container := input.review.object.spec.template.spec.containers[_]\n'
    '    not container.resources.limits.cpu\n'
    '    msg := sprintf("Container \'%v\' must set a CPU limit", [container.name])\n'
    '}\n\n'
    'violation[{"msg": msg}] if {\n'
    '    container := input.review.object.spec.template.spec.containers[_]\n'
    '    not container.resources.limits.memory\n'
    '    msg := sprintf("Container \'%v\' must set a memory limit", [container.name])\n'
    '}\n\n'
    'violation[{"msg": msg}] if {\n'
    '    container := input.review.object.spec.template.spec.containers[_]\n'
    '    not container.resources.requests.cpu\n'
    '    msg := sprintf("Container \'%v\' must set a CPU request", [container.name])\n'
    '}'
)
doc.add_paragraph("Constraint (kubernetes/gatekeeper/constraints/require-resource-limits.yaml): kind K8sRequireResourceLimits, name require-resource-limits.")
doc.add_table(
    headers=["Parameter", "Value"],
    rows=[
        ["match.kinds", "apiGroups: [apps], kinds: [Deployment, DaemonSet, StatefulSet]"],
        ["match.excludedNamespaces", "kube-system"],
        ["enforcementAction", "deny"],
    ],
)

doc.add_heading2("3.4 CI-time standalone OPA policies (opa/policies/)")
doc.add_paragraph(
    "These three files are independent of the Gatekeeper templates above (different package "
    "name, different input shape \u2014 input is the raw manifest, not a Gatekeeper "
    "AdmissionReview under input.review.object) and are evaluated directly via opa eval "
    "rather than through a cluster admission webhook."
)
doc.add_table(
    headers=["File", "Package", "Rules"],
    rows=[
        ["opa/policies/deny-privileged.rego", "kubernetes", "Denies privileged containers, hostPID: true, and hostNetwork: true on any Deployment"],
        ["opa/policies/require-labels.rego", "kubernetes", "Denies a Deployment (and separately its pod template) missing any of the required_labels set: app, version, team, env"],
        ["opa/policies/resource-limits.rego", "kubernetes", "Denies a container missing resources.limits.cpu, resources.limits.memory, or resources.requests.cpu"],
    ],
)

# ------------------------------------------------------------------
# 4. CI/CD pipeline stage reference
# ------------------------------------------------------------------
doc.add_heading1("4. CI/CD pipeline stage reference")
doc.add_paragraph("This section replaces a traditional API specification, since this repository exposes no application API surface \u2014 its real \u201cinterface\u201d is the pipeline's stage graph.")
doc.add_table(
    headers=["Stage", "Tool", "Trigger condition", "Pass/fail behavior"],
    rows=[
        ["sast", "Bandit + Semgrep", "push/PR to main or develop", "Fails on Bandit medium+ severity/confidence finding; Semgrep never fails (continue-on-error)"],
        ["sca", "Safety", "push/PR to main or develop", "Never fails (|| true); report-only"],
        ["iac-scan", "Checkov (terraform + kubernetes frameworks)", "push/PR to main or develop", "Never fails (soft_fail: true); SARIF-only"],
        ["container-scan", "Docker Buildx + Trivy", "push/PR to main or develop, needs: [sast, sca]", "Fails on any CRITICAL image CVE (Trivy run #1); HIGH+CRITICAL scan and fs scan are informational; image push gated behind all of the above plus github.ref == refs/heads/main"],
        ["sbom", "Syft", "push/PR to main or develop, needs: [container-scan]", "No pass/fail condition; pure artifact generation"],
        ["opa-check", "OPA (opa eval x3)", "push/PR to main or develop", "Exits 0 regardless of deny-set contents (no --fail-defined); violations are logged, not gating"],
        ["security-report", "scripts/security-report.py", "push/PR to main or develop, needs: all jobs, if: always()", "No pass/fail condition; posts a PR comment when event is pull_request"],
        ["full-scan", "Trivy (fs, MEDIUM/HIGH/CRITICAL)", "cron '0 2 * * 1' or workflow_dispatch (scheduled-scan.yaml)", "No pass/fail condition; SARIF upload only"],
    ],
)

# ------------------------------------------------------------------
# 5. Sequence flows / process flows
# ------------------------------------------------------------------
doc.add_heading1("5. Sequence flows / process flows")

doc.add_heading2("5.1 Flow: pull request triggers scan gates before merge")
doc.add_table(
    headers=["Step", "Actor / component", "Action"],
    rows=[
        ["1", "Developer", "Opens a pull request against main"],
        ["2", "GitHub Actions", "Triggers devsecops-pipeline.yaml on the pull_request event"],
        ["3", "sast job", "Runs Bandit (blocking) + Semgrep (advisory) against app/"],
        ["4", "sca job", "Runs Safety (advisory, || true) against app/requirements.txt, in parallel with sast"],
        ["5", "iac-scan job", "Runs Checkov (advisory, soft_fail) against terraform/ and kubernetes/, in parallel with sast/sca"],
        ["6", "container-scan job", "Waits on sast + sca; builds the image; runs blocking CRITICAL Trivy scan"],
        ["7", "container-scan job", "If CRITICAL scan passes, runs advisory HIGH+CRITICAL and fs scans; does NOT push (ref is a PR, not main)"],
        ["8", "opa-check job", "Evaluates kubernetes/deployment.yaml against the three Rego policies; logs any violations"],
        ["9", "security-report job", "Waits on all jobs (if: always()); downloads Bandit/Safety artifacts; posts security-summary.md as a PR comment"],
        ["10", "Reviewer", "Merges the PR based on required-check status (Bandit/Trivy CRITICAL) plus manual review of the Security tab / PR comment for advisory findings"],
    ],
)

doc.add_heading2("5.2 Flow: merge to main triggers image push")
doc.add_table(
    headers=["Step", "Actor / component", "Action"],
    rows=[
        ["1", "Developer / reviewer", "Merges the PR into main"],
        ["2", "GitHub Actions", "Triggers devsecops-pipeline.yaml on the push event, github.ref == refs/heads/main"],
        ["3", "sast, sca, iac-scan jobs", "Run identically to the PR flow"],
        ["4", "container-scan job", "Builds the image, runs the blocking CRITICAL Trivy scan; on success, runs the final docker/build-push-action step with push: true (because ref == refs/heads/main)"],
        ["5", "GHCR", "Receives the pushed image tagged sha-<sha>, main, and any matching semver tag"],
        ["6", "sbom job", "Generates SPDX + CycloneDX SBOMs for the app/ source, uploaded as artifacts"],
        ["7", "(manual, out of pipeline)", "A cluster operator may later kubectl apply the image reference / kubernetes/deployment.yaml to a live cluster"],
    ],
)

doc.add_heading2("5.3 Flow: admission-time Gatekeeper evaluation on a live cluster")
doc.add_table(
    headers=["Step", "Actor / component", "Action"],
    rows=[
        ["1", "Cluster operator", "Runs kubectl apply -f kubernetes/gatekeeper/constraint-templates/ then kubernetes/gatekeeper/constraints/ once, to install the three policies"],
        ["2", "Cluster operator", "Runs kubectl apply -f kubernetes/deployment.yaml (or any other Deployment/DaemonSet/StatefulSet manifest)"],
        ["3", "Kubernetes API server", "Invokes the Gatekeeper validating admission webhook before persisting the object"],
        ["4", "Gatekeeper", "Evaluates K8sBlockPrivileged, K8sRequireNonRoot (Deployments only), and K8sRequireResourceLimits against the incoming object"],
        ["5a", "Gatekeeper (compliant case)", "No violation[] results produced; the API server admits the object"],
        ["5b", "Gatekeeper (non-compliant case)", "violation[{\"msg\": ...}] is non-empty; enforcementAction: deny causes the API server to reject the request with the Rego msg surfaced in the error response"],
    ],
)

doc.add_heading2("5.4 Flow: weekly scheduled full filesystem scan")
doc.add_table(
    headers=["Step", "Actor / component", "Action"],
    rows=[
        ["1", "GitHub Actions scheduler", "Fires cron '0 2 * * 1' (or a manual workflow_dispatch) on scheduled-scan.yaml"],
        ["2", "full-scan job", "Checks out the repository at its current main state"],
        ["3", "Trivy (fs scan)", "Scans the entire filesystem at severity MEDIUM,HIGH,CRITICAL, writing weekly-trivy.sarif"],
        ["4", "github/codeql-action/upload-sarif", "Uploads the SARIF under category weekly-scan to the Security tab"],
        ["5", "Security team", "Reviews newly surfaced findings (e.g. CVEs disclosed after the last code change) independent of any code push"],
    ],
)

# ------------------------------------------------------------------
# 6. Key algorithms & business logic
# ------------------------------------------------------------------
doc.add_heading1("6. Key algorithms & business logic")

doc.add_heading2("6.1 Severity-threshold gating")
doc.add_bullets([
    "Bandit: --severity-level medium --confidence-level medium on the unsuppressed run in "
    "sast \u2014 both severity AND confidence must be at least medium for the finding to surface, "
    "and the job fails if bandit's own exit code is non-zero (Bandit exits non-zero whenever "
    "any finding at/above the given thresholds exists).",
    "Trivy (blocking run): severity: CRITICAL, vuln-type: os,library, exit-code: \"1\" \u2014 "
    "the action fails the step (and therefore the job) if at least one CRITICAL CVE is found "
    "in either OS packages or language libraries in the built image.",
    "Trivy (informational runs): severity: HIGH,CRITICAL (image) and scanners: misconfig,secret "
    "(filesystem) with no exit-code override \u2014 these always produce a report but never fail "
    "the step.",
    "OPA (opa eval): no severity concept at all \u2014 every deny rule in the three Rego files is "
    "a hard boolean violation (privileged=true, missing label, missing resource field), but "
    "because --fail-defined is absent, ALL of them are currently non-blocking regardless of "
    "how many violations are found.",
    "Gatekeeper: no severity concept either \u2014 every violation[] result under "
    "enforcementAction: deny blocks the API request outright; there is no warn-only tier "
    "configured for any of the three Constraints in this repo (Gatekeeper does support a "
    "dryrun/warn enforcementAction, but it is not used here).",
])

doc.add_heading2("6.2 Waiver / exemption mechanisms")
doc.add_paragraph(
    "There is no formal waiver or exemption mechanism (e.g. a Checkov .checkov.yaml skip "
    "list, a Trivy .trivyignore file, or a Gatekeeper exempt-namespace label mechanism beyond "
    "excludedNamespaces) present in this repository. The closest thing to an exemption is the "
    "static excludedNamespaces list on each Constraint (kube-system for all three; "
    "additionally monitoring for K8sRequireNonRoot) \u2014 these are hardcoded in the Constraint "
    "manifests, not configurable per-request, and there is no annotation-based per-workload "
    "override. Any true exemption today requires editing the Constraint YAML and "
    "re-applying it to the cluster."
)

doc.add_heading2("6.3 Label-requirement logic (require-labels.rego)")
doc.add_paragraph(
    "required_labels := {\"app\", \"version\", \"team\", \"env\"} is checked twice per manifest: "
    "once against input.metadata.labels (the Deployment object's own labels) and once against "
    "input.spec.template.metadata.labels (the pod template's labels), each producing a "
    "separate deny message per missing label per location \u2014 so a Deployment missing all four "
    "labels in both places can produce up to eight distinct deny messages in one evaluation."
)

# ------------------------------------------------------------------
# 7. Validation & error handling
# ------------------------------------------------------------------
doc.add_heading1("7. Validation & error handling")
doc.add_paragraph(
    "This pipeline uses three distinct failure-handling patterns, and understanding which "
    "pattern applies to which stage is essential to interpreting a red/green pipeline run "
    "correctly."
)
doc.add_bullets([
    "Hard block (job fails, PR check fails): the unsuppressed Bandit run in sast, and the "
    "CRITICAL-only Trivy run in container-scan. A failure here stops container-scan from "
    "reaching its push step and is visible as a failed required check on the PR.",
    "Soft/advisory (job succeeds, findings surfaced elsewhere): Semgrep (continue-on-error), "
    "Safety (|| true), both Checkov runs (soft_fail: true), the HIGH+CRITICAL Trivy image "
    "scan and the Trivy fs scan (no exit-code override), and all three opa-check evaluations "
    "(no --fail-defined). These always let the job succeed; a developer must actively check "
    "the Security tab or the PR comment to see what they found.",
    "Hard block at a different layer entirely (cluster admission, not CI): Gatekeeper's three "
    "Constraints use enforcementAction: deny, so a non-compliant manifest applied directly to "
    "a Gatekeeper-enabled cluster is rejected by the API server \u2014 this happens independent "
    "of, and later than, anything CI did.",
])
doc.add_paragraph(
    "Known gaps: (1) the opa-check job's advisory-only behavior is likely unintentional given "
    "the README's Security Gates section states OPA/Gatekeeper \"blocks deployment\" \u2014 that "
    "claim is accurate for the Gatekeeper layer but not for the CI-time opa eval steps as "
    "currently flagged; (2) trivy-fs.sarif is generated in container-scan but has no "
    "corresponding upload-sarif step, so filesystem/secret findings from that particular run "
    "are not currently surfaced anywhere, not even the Security tab; (3) "
    "scripts/security-report.py silently omits Checkov and Trivy findings from its "
    "PR-comment summary \u2014 a reviewer relying solely on the PR comment (rather than also "
    "checking the Security tab) would miss those two tools' output entirely; (4) there is no "
    "retry or timeout handling around the curl-based OPA/Syft installs, so a transient "
    "network failure during those installs fails the whole job with a generic shell error "
    "rather than a security-specific one."
)

# ------------------------------------------------------------------
# 8. Non-functional implementation details
# ------------------------------------------------------------------
doc.add_heading1("8. Non-functional implementation details")

doc.add_heading2("8.1 Security implementation specifics")
doc.add_bullets([
    "The demo app's own Dockerfile creates a dedicated non-root user (groupadd --gid 10001 "
    "appgroup, useradd --uid 10001) and USER appuser before CMD, so the image itself is built "
    "non-root regardless of the Gatekeeper/OPA policies that later re-check this at the "
    "Kubernetes layer.",
    "app/Dockerfile also defines a HEALTHCHECK hitting /health, matching the /health and "
    "/ready endpoints in app/app.py used by the Kubernetes liveness/readiness probes in "
    "kubernetes/deployment.yaml.",
    "docker/login-action@v3 authenticates to ghcr.io using the ephemeral secrets.GITHUB_TOKEN "
    "rather than a long-lived PAT, scoped by the workflow's own permissions.packages: write.",
    "kubernetes/deployment.yaml sets automountServiceAccountToken: false, reducing the blast "
    "radius if the pod were ever compromised, and readOnlyRootFilesystem: true plus an "
    "explicit emptyDir volume mounted at /tmp to give the app a writable scratch directory "
    "without a writable root filesystem.",
])

doc.add_heading2("8.2 Pipeline-speed / performance considerations")
doc.add_bullets([
    "sast, sca, and iac-scan have no needs: dependency on each other, so GitHub Actions "
    "schedules them concurrently, bounding wall-clock time to roughly the slowest of the "
    "three rather than their sum.",
    "docker/build-push-action@v5 uses cache-from/cache-to: type=gha, reusing GitHub Actions' "
    "own cache backend across runs to avoid re-downloading/re-installing Python dependencies "
    "in the image on every build.",
    "The container-scan job's final push step is conditioned on github.ref == "
    "'refs/heads/main', so feature-branch and PR runs never pay the cost (or risk) of a "
    "registry push \u2014 they still build and scan the image locally (load: true) for gating "
    "purposes.",
    "OPA and Syft binaries are downloaded fresh on every single run rather than cached or "
    "baked into a custom runner image, which is simple but adds network I/O time (and a "
    "dependency on external endpoint availability) to every pipeline execution.",
])

# ------------------------------------------------------------------
# 9. Appendix
# ------------------------------------------------------------------
doc.add_heading1("9. Appendix")

doc.add_heading2("9.1 Repo module / file map")
doc.add_code_block(
    ".\n"
    "|-- app/                                   # Flask demo application (scan target)\n"
    "|   |-- app.py                             # /, /health, /ready endpoints\n"
    "|   |-- requirements.txt                   # flask==3.0.3, gunicorn==22.0.0 (SCA target)\n"
    "|   `-- Dockerfile                         # non-root build, gunicorn entrypoint\n"
    "|-- kubernetes/\n"
    "|   |-- deployment.yaml                    # hardened sample Deployment (OPA + Gatekeeper input)\n"
    "|   `-- gatekeeper/\n"
    "|       |-- constraint-templates/\n"
    "|       |   |-- block-privileged.yaml      # K8sBlockPrivileged\n"
    "|       |   |-- require-non-root.yaml      # K8sRequireNonRoot\n"
    "|       |   `-- require-resource-limits.yaml # K8sRequireResourceLimits\n"
    "|       `-- constraints/\n"
    "|           |-- block-privileged.yaml       # binds K8sBlockPrivileged\n"
    "|           |-- require-non-root.yaml        # binds K8sRequireNonRoot\n"
    "|           `-- require-resource-limits.yaml # binds K8sRequireResourceLimits\n"
    "|-- opa/\n"
    "|   `-- policies/                          # standalone CI-time Rego (opa eval)\n"
    "|       |-- deny-privileged.rego\n"
    "|       |-- require-labels.rego\n"
    "|       `-- resource-limits.rego\n"
    "|-- scripts/\n"
    "|   `-- security-report.py                 # Bandit + Safety -> security-summary.md\n"
    "|-- terraform/\n"
    "|   `-- main.tf                            # hardened S3 bucket (Checkov IaC target)\n"
    "`-- .github/workflows/\n"
    "    |-- devsecops-pipeline.yaml            # sast, sca, iac-scan, container-scan, sbom,\n"
    "    |                                      # opa-check, security-report\n"
    "    `-- scheduled-scan.yaml                # weekly full-scan (Trivy fs, cron)\n"
)

doc.add_heading2("9.2 Environment variable / configuration reference")
doc.add_table(
    headers=["Name", "Defined in", "Meaning"],
    rows=[
        ["IMAGE_NAME", "devsecops-pipeline.yaml env block", "devsecops-app \u2014 base image name"],
        ["REGISTRY", "devsecops-pipeline.yaml env block", "ghcr.io \u2014 target container registry"],
        ["APP_VERSION", "app/app.py os.getenv", "Runtime display value on the / endpoint; defaults to 1.0.0 if unset"],
        ["GITHUB_TOKEN", "GitHub Actions implicit secret", "Used by docker/login-action for GHCR auth and by actions/github-script for the PR comment"],
        ["permissions.contents", "both workflows", "read \u2014 checkout access only"],
        ["permissions.security-events", "both workflows", "write \u2014 required to upload SARIF to Code Scanning"],
        ["permissions.pull-requests", "devsecops-pipeline.yaml", "write \u2014 required to post the security-summary.md PR comment"],
        ["permissions.packages", "devsecops-pipeline.yaml", "write \u2014 required to push images to GHCR"],
        ["cron schedule", "scheduled-scan.yaml", "'0 2 * * 1' \u2014 every Monday 02:00 UTC"],
    ],
)

doc.add_heading2("9.3 Change history")
doc.add_table(
    headers=["Version", "Date", "Description"],
    rows=[
        ["1.0", DATE, "Initial low-level design document"],
    ],
)

doc.save("D:/Projects/DevOps/Darviq-DevSecOps/Docs/Darviq_DevSecOps_Low_Level_Design.docx")
print("LLD saved.")
