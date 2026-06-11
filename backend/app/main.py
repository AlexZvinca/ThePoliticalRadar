from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.aggregates import build_aggregates
from app.config import get_settings
from app.connectors.csv_connector import parse_csv_items
from app.domain import Analysis, AnalysisRequest, AnalysisStatus, SourceName
from app.integration_status import IntegrationStatus
from app.pipeline import run_analysis
from app.repository import repository
from app.sentiment import SentimentAnalyzer
from app.utils import deduplicate_items

app = FastAPI(title="The Political Radar API", version="0.1.0")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "the-political-radar"}


@app.get("/integrations/status", response_model=IntegrationStatus)
async def integration_status() -> IntegrationStatus:
    settings = get_settings()
    azure_status = await SentimentAnalyzer(settings).check_azure_connection()
    return IntegrationStatus(
        azure_language=azure_status,
        youtube_configured=bool(settings.youtube_api_key),
        database_configured=bool(settings.database_url),
    )


@app.post("/analyses", response_model=Analysis)
async def create_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks) -> Analysis:
    analysis = repository.save(Analysis(request=request))
    background_tasks.add_task(_execute_analysis, analysis.id)
    return analysis


@app.get("/analyses", response_model=list[Analysis])
def list_analyses() -> list[Analysis]:
    return repository.list()


@app.get("/analyses/{analysis_id}", response_model=Analysis)
def get_analysis(analysis_id: str) -> Analysis:
    analysis = repository.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.post("/uploads/csv", response_model=Analysis)
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    entity: str = "Uploaded entity",
    country: str = "Unknown",
    language: str = "auto",
) -> Analysis:
    content = (await file.read()).decode("utf-8-sig")
    items = deduplicate_items(parse_csv_items(content))[:1000]
    if not items:
        raise HTTPException(status_code=422, detail="CSV must include a text/comment/body column")

    dates = [item.published_at.date() for item in items]
    request = AnalysisRequest(
        entity=entity,
        country=country,
        start_date=min(dates),
        end_date=max(dates),
        sources=[SourceName.csv],
        language=language,
        limit_per_source=len(items),
    )
    analysis = Analysis(request=request, status=AnalysisStatus.running, items=items)
    repository.save(analysis)
    background_tasks.add_task(_execute_uploaded_analysis, analysis.id)
    return analysis


async def _execute_analysis(analysis_id: str) -> None:
    analysis = repository.get(analysis_id)
    if not analysis:
        return
    await run_analysis(analysis, get_settings())
    repository.save(analysis)


async def _execute_uploaded_analysis(analysis_id: str) -> None:
    analysis = repository.get(analysis_id)
    if not analysis:
        return
    settings = get_settings()
    sentiments = await SentimentAnalyzer(settings).analyze(
        analysis.items,
        analysis.request.language,
        analysis.request.entity,
    )
    analysis.sentiments = sentiments
    analysis.aggregates = build_aggregates(analysis.items, sentiments, [])
    analysis.status = AnalysisStatus.completed
    analysis.touch()
    repository.save(analysis)
