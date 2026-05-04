# Automated deploy: GitHub Actions → Artifact Registry → Cloud Run

The workflow **`.github/workflows/ci.yml`** deploys only on **`push` to `main`**, after **backend tests**, **frontend build**, and **stub eval** succeed.

## What the deploy job does

1. Authenticates with Google using **`GCP_SA_KEY`** (JSON for a **deployer** service account).
2. Builds and pushes **`candid-backend`** and **`candid-frontend`** images to **Artifact Registry** (tag = commit SHA).
3. Deploys **backend** Cloud Run (port **8080**) with **`ANTHROPIC_API_KEY`** from GitHub or from **Secret Manager** (see below).
4. Deploys **frontend** Cloud Run (port **80**) with **`VITE_API_BASE_URL`** baked to `{backend_url}/api/v1`.
5. Updates the backend with **`FRONTEND_ORIGIN`** so FastAPI CORS matches the frontend URL.

To use different Cloud Run service names, edit the **`BACKEND_SERVICE`** / **`FRONTEND_SERVICE`** values in **`ci.yml`** (currently `candid-backend` and `candid-frontend`).

## GitHub Actions secrets (repository)

| Secret | Required | Purpose |
|--------|----------|---------|
| **`GCP_SA_KEY`** | Yes | Full JSON key for the **deployer** service account (CI pushes images and deploys Cloud Run). |
| **`GCP_PROJECT_ID`** | Yes | GCP project id (e.g. `candid-490020`). |
| **`GCP_REGION`** | Yes | Region for Artifact Registry + Cloud Run (e.g. `us-central1`). |
| **`ARTIFACT_REGISTRY_REPO`** | Yes | Artifact Registry **repository name** (Docker). |
| **`ANTHROPIC_API_KEY`** | One of two | Anthropic API key stored in GitHub; workflow sets Cloud Run env var **`ANTHROPIC_API_KEY`**. Easiest for class projects. |
| **`GSM_ANTHROPIC_SECRET`** | One of two | **Secret Manager secret id** (not the key text); workflow uses **`--set-secrets`**. Prefer for production. |
| **`CLOUDRUN_RUNTIME_SA`** | If using GSM | Email of the **runtime** service account Cloud Run runs as; must have **`roles/secretmanager.secretAccessor`** on the Anthropic secret. |

Use **either** `ANTHROPIC_API_KEY` **or** `GSM_ANTHROPIC_SECRET` + `CLOUDRUN_RUNTIME_SA`, not both for the same purpose (if both are set, the workflow prefers **GSM**).

## GCP setup checklist (one-time)

1. **Billing** enabled on the project.
2. Enable **Cloud Run**, **Artifact Registry**, **Secret Manager** (and **IAM** as needed).
3. Create an **Artifact Registry** repository (format `REGION-docker.pkg.dev/PROJECT/REPO/...`). Put its **repository id** in **`ARTIFACT_REGISTRY_REPO`**.
4. Create a **deployer** service account (e.g. `github-deployer`) and grant it at least:
   - **`roles/run.admin`** — deploy Cloud Run services  
   - **`roles/artifactregistry.writer`** — push images  
   - **`roles/iam.serviceAccountUser`** — deploy revisions that use another service account as runtime identity (when **`CLOUDRUN_RUNTIME_SA`** is set)  
5. Create a **JSON key** for the deployer (IAM → Service accounts → Keys) and paste the **entire JSON** into GitHub secret **`GCP_SA_KEY`**. Treat it like a password; rotate if leaked. (Long term, prefer **Workload Identity Federation** and remove JSON keys.)
6. Create a **runtime** service account (e.g. `candid-backend-runtime`) for the backend service. If using **GSM** for Anthropic:
   - Create Secret Manager secret (e.g. id **`anthropic-api-key`**) with the Anthropic key value.
   - Grant **`roles/secretmanager.secretAccessor`** on that secret to **`candid-backend-runtime`**.
   - Put secret id in **`GSM_ANTHROPIC_SECRET`** and runtime email in **`CLOUDRUN_RUNTIME_SA`**.
7. First deploy will create Cloud Run services **`candid-backend`** and **`candid-frontend`** if they do not exist. Ensure **project-level** quotas and org policies allow Cloud Run + Artifact Registry.

## After the first successful deploy

- Open the **frontend** service URL in a browser and try chat.
- If CORS fails, confirm the **`Point backend CORS`** step ran and **`FRONTEND_ORIGIN`** on the backend matches the frontend URL (scheme + host, no trailing path).

## Optional hardening

- Replace **`GCP_SA_KEY`** with **Workload Identity Federation** (`google-github-actions/auth` with `workload_identity_provider` + `service_account`) so no JSON key is stored in GitHub.
- Lock deploy to a specific environment with **GitHub Environments** + protection rules.
- Add **`--vpc-connector`** only if you need private egress or VPC resources.
