# The Political Radar

Cloud-based political sentiment analysis dashboard for the Cloud Based AI Services course.

The app lets a user search for a politician or political party by country and date range, gathers public text from News RSS, YouTube comments, and CSV uploads, runs sentiment analysis, and presents visualization-heavy public opinion trends.

## Architecture

```text
React + TypeScript dashboard
        |
        v
Python FastAPI backend
        |
        +-- News RSS connector
        +-- YouTube connector
        +-- CSV upload connector
        |
        v
Sentiment pipeline
        |
        +-- Azure AI Language when credentials are configured
        +-- deterministic local analyzer as demo fallback
        |
        v
PostgreSQL-ready persistence schema
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Environment variables:

- `AZURE_LANGUAGE_ENDPOINT`
- `AZURE_LANGUAGE_KEY`
- `YOUTUBE_API_KEY`
- `DATABASE_URL`

If Azure credentials are missing, the backend uses a deterministic local sentiment analyzer so the demo still works.

Copy `backend/.env.example` to `backend/.env` and paste the Azure values there when the Azure AI Language resource is ready.

Check Azure AI Language locally:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\check_azure_language.py
```

Or with the API running:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/integrations/status
```

Wikipedia profile images require a Wikimedia-compliant User-Agent. In `backend/.env`, replace the example contact with a real email/contact:

```env
WIKIMEDIA_USER_AGENT=ThePoliticalRadar/0.1 (student project; contact: your.email@example.com)
```

## Frontend

PowerShell may block `npm.ps1`; use `npm.cmd`.

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

The frontend expects the API at `http://localhost:8000` unless `VITE_API_BASE_URL` is set.

## Tests

```powershell
cd backend
python -m unittest discover -s tests
```

## Simplest Demo Deployment

The simplest reliable demo keeps the backend local and uses Azure only for AI sentiment analysis.

1. Create an Azure AI Language resource in Azure Portal.
2. Copy `backend/.env.example` to `backend/.env`.
3. Set:

```env
AZURE_LANGUAGE_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com/
AZURE_LANGUAGE_KEY=your_key_here
YOUTUBE_API_KEY=your_youtube_key_here
WIKIMEDIA_USER_AGENT=ThePoliticalRadar/0.1 (student project; contact: your.email@example.com)
```

4. Start the backend locally:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5. Start the frontend locally:

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

6. Open:

```text
http://127.0.0.1:5173
```

7. Confirm integrations:

```text
http://127.0.0.1:8000/integrations/status
```

For an optional frontend-only cloud deployment, build with the local backend URL:

```powershell
cd frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm.cmd run build
```

Then upload `frontend/dist` to Azure Static Web Apps or any static hosting service. For the classroom demo, local frontend + local backend + Azure AI Language is the least fragile setup.

## Demo Flow

1. Start the backend.
2. Start the frontend.
3. Run a search for a politician or party.
4. Use `sources = news` for live no-key data, `youtube` for public comments, or `csv` for a deterministic demo path.
5. Inspect sentiment trends, distribution, source split, peaks, events, key phrases, and representative comments.

## Data Limits

- Maximum date range: 3 years.
- Default limit: 250 items per source.
- Maximum limit: 1,000 items per source.
- News RSS is the default live source because it works without approval.
- YouTube comments are the preferred public-comment source when `YOUTUBE_API_KEY` is configured.
- CSV upload remains the guaranteed presentation fallback.

## Responsible Data Use

This project is designed as a non-commercial academic demo using official APIs.

- Respect platform rate limits and terms.
- Store only short public text excerpts for visualization.
- Do not store YouTube usernames in analysis results.
- Link back to original source URLs when available.
- Do not train or fine-tune AI models on YouTube content.
- Delete cached/exported public-source data if API access is revoked or the data is no longer needed.
- Present results as sampled public commentary, not as a definitive measure of national opinion.
