## UofA Course Graph

Interactive prerequisite and dependency graph explorer for any course at the University of Alberta.

## Stack

- **App:** React, TypeScript, Vite, vis-network, FastAPI, psycopg
- **Data:** PostgreSQL (Supabase)
- **Deploy:** Vercel (web), AWS Lambda via SAM (API)

## Documentation

Technical docs: [docs/](docs/) — [data pipeline](docs/DATA_PIPELINE.md) and [application](docs/APPLICATION.md).

## Local development

### Python

1. Create and activate a Python virtual environment at the repo root.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### API
3. Set `DATABASE_URL=postgresql://...` in a repo-root `.env`
4. Start the API:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Web UI

1. Install dependencies:
   ```bash
   cd uofa-course-graph
   npm install
   ```
2. Start the dev server:
   ```bash
   npm run dev -- --host
   ```
3. Open `http://localhost:5173`

For a phone on the same Wi‑Fi, set `VITE_API_BASE_URL=http://YOUR_PC_LAN_IP:8000` in `uofa-course-graph/.env.development.local` and add `CORS_EXTRA_ORIGINS=http://YOUR_PC_LAN_IP:5173` for the API. See the app README for more.

### Scraper 

```bash
python run_scrape_add.py       # scrape + load in one step
```

## API overview

- `GET /health` — health check
- `GET /courses` — list course codes and titles
- `GET /courses/{code}` — one course record
- `GET /graph/{code}` — graph payload (`max_depth`, `include_coreqs`, `view=prereq|dependency`)

## Deploy API (GitHub Actions)

Workflow: [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml). Runs on pushes to `main` that change API/SAM files, or manually via **Actions → Deploy backend (AWS SAM) → Run workflow**.

### GitHub configuration

| Kind | Name | Required | Notes |
|------|------|----------|--------|
| Secret | `DATABASE_URL` | Yes | PostgreSQL URL for Lambda (`postgresql://...`) |
| Secret | `AWS_DEPLOY_ROLE_ARN` | Yes | IAM role ARN for OIDC deploy (see below) |
| Secret | `CORS_EXTRA_ORIGINS` | No | Defaults to `https://uofa-course-graph.vercel.app` |
| Variable | `AWS_REGION` | No | Defaults to `us-east-1` |
| Variable | `SAM_STACK_NAME` | No | Defaults to `uofa-prereq-api` |

Set secrets/variables under **GitHub repo → Settings → Secrets and variables → Actions**.

`DATABASE_URL` alone is not enough — the workflow must assume an AWS role to run `sam deploy`.

### One-time AWS setup (OIDC)

1. **OIDC provider** (once per AWS account): IAM → Identity providers → Add provider → OpenID Connect → URL `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`.

2. **Deploy role**: IAM → Roles → Create role → Web identity → select the GitHub OIDC provider → use trust policy [`.github/aws/github-actions-deploy-trust.json`](.github/aws/github-actions-deploy-trust.json) (replace `YOUR_ACCOUNT_ID`). Restrict `sub` to your repo/branch if the repo name differs from `judxyz/ua-prereq`.

3. **Permissions**: attach policies that allow SAM to create/update the stack (e.g. `AdministratorAccess` for a personal account, or scoped CloudFormation + Lambda + API Gateway + S3 + IAM policies).

4. Copy the role **ARN** into GitHub secret `AWS_DEPLOY_ROLE_ARN`.

5. Run the workflow (or push an API change). After success, read stack output **ApiUrl** in CloudFormation and set `VITE_API_BASE_URL` on Vercel to that URL.

Frontend-only changes under `uofa-course-graph/src/` do not trigger this workflow.
