import React from "react";
import { createRoot } from "react-dom/client";
import { BarChart3, FileUp, History, Radar, Search } from "lucide-react";
import * as echarts from "echarts";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type SourceName = "news" | "youtube" | "csv";
type SentimentLabel = "positive" | "neutral" | "negative" | "mixed";
type AnalysisStatus = "queued" | "running" | "completed" | "failed";

type AnalysisRequest = {
  entity: string;
  country: string;
  start_date: string;
  end_date: string;
  sources: SourceName[];
  language: string;
  limit_per_source: number;
};

type SourceItem = {
  id: string;
  source: SourceName;
  text: string;
  published_at: string;
  title?: string;
  author?: string;
  url?: string;
};

type DailyPoint = {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  mixed: number;
  average_score: number;
  volume: number;
};

type AggregateSnapshot = {
  total_items: number;
  sentiment_distribution: Record<SentimentLabel, number>;
  source_distribution: Record<SourceName, number>;
  daily: DailyPoint[];
  peaks: { date: string; volume: number; negative_share: number; note: string }[];
  key_phrases: [string, number][];
  representatives: Record<SentimentLabel, SourceItem[]>;
  events: { date: string; title: string; source: string; url?: string }[];
};

type EntityProfile = {
  title: string;
  description?: string;
  extract?: string;
  image_url?: string;
  page_url?: string;
  source: string;
};

type Analysis = {
  id: string;
  request: AnalysisRequest;
  status: AnalysisStatus;
  created_at: string;
  updated_at: string;
  error?: string;
  warnings: string[];
  profile?: EntityProfile;
  aggregates?: AggregateSnapshot;
};

type IntegrationStatus = {
  azure_language: {
    configured: boolean;
    ok: boolean;
    mode: string;
    message: string;
  };
  youtube_configured: boolean;
  database_configured: boolean;
};

const defaultRequest: AnalysisRequest = {
  entity: "Example Party",
  country: "Romania",
  start_date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14).toISOString().slice(0, 10),
  end_date: new Date().toISOString().slice(0, 10),
  sources: ["news", "youtube"],
  language: "auto",
  limit_per_source: 250,
};

const sourceLabels: Record<SourceName, string> = {
  csv: "CSV",
  news: "News RSS",
  youtube: "YouTube",
};

const countryOptions = [
  "Romania",
  "United States",
  "United Kingdom",
  "France",
  "Germany",
  "Italy",
  "Spain",
  "Poland",
  "Netherlands",
  "Belgium",
  "Hungary",
  "Moldova",
  "Ukraine",
];

const languageOptions = [
  { code: "auto", label: "Automatic" },
  { code: "ro", label: "Romanian" },
  { code: "en", label: "English" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "es", label: "Spanish" },
  { code: "pl", label: "Polish" },
  { code: "hu", label: "Hungarian" },
  { code: "uk", label: "Ukrainian" },
];

function App() {
  const [request, setRequest] = React.useState<AnalysisRequest>(defaultRequest);
  const [dateInputs, setDateInputs] = React.useState({
    start_date: formatDateForDisplay(defaultRequest.start_date),
    end_date: formatDateForDisplay(defaultRequest.end_date),
  });
  const [limitInput, setLimitInput] = React.useState(String(defaultRequest.limit_per_source));
  const [analysis, setAnalysis] = React.useState<Analysis | null>(null);
  const [history, setHistory] = React.useState<Analysis[]>([]);
  const [integrationStatus, setIntegrationStatus] = React.useState<IntegrationStatus | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    void refreshHistory();
    void refreshIntegrationStatus();
  }, []);

  React.useEffect(() => {
    if (!analysis || analysis.status === "completed" || analysis.status === "failed") {
      return;
    }
    const handle = window.setInterval(async () => {
      const next = await fetchAnalysis(analysis.id);
      setAnalysis(next);
      if (next.status === "completed" || next.status === "failed") {
        window.clearInterval(handle);
        void refreshHistory();
      }
    }, 1200);
    return () => window.clearInterval(handle);
  }, [analysis]);

  async function refreshHistory() {
    try {
      const response = await fetch(`${API_BASE_URL}/analyses`);
      if (response.ok) {
        setHistory(await response.json());
      }
    } catch {
      setHistory([]);
    }
  }

  async function refreshIntegrationStatus() {
    try {
      const response = await fetch(`${API_BASE_URL}/integrations/status`);
      if (response.ok) {
        setIntegrationStatus(await response.json());
      }
    } catch {
      setIntegrationStatus(null);
    }
  }

  async function fetchAnalysis(id: string): Promise<Analysis> {
    const response = await fetch(`${API_BASE_URL}/analyses/${id}`);
    if (!response.ok) {
      throw new Error("Could not load analysis");
    }
    return response.json();
  }

  async function submitAnalysis(event: React.FormEvent) {
    event.preventDefault();
    const startDate = parseDisplayDate(dateInputs.start_date);
    const endDate = parseDisplayDate(dateInputs.end_date);
    if (!startDate || !endDate) {
      setError("Dates must use DD/MM/YYYY format.");
      return;
    }
    const limitPerSource = Number(limitInput);
    if (!Number.isInteger(limitPerSource) || limitPerSource < 5 || limitPerSource > 1000) {
      setError("Limit/source must be a whole number between 5 and 1000.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/analyses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...request, start_date: startDate, end_date: endDate, limit_per_source: limitPerSource }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setAnalysis(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function uploadCsv(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/uploads/csv?entity=${encodeURIComponent(request.entity)}&country=${encodeURIComponent(
          request.country,
        )}&language=${encodeURIComponent(request.language)}`,
        { method: "POST", body: form },
      );
      if (!response.ok) throw new Error(await response.text());
      setAnalysis(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
      event.target.value = "";
    }
  }

  return (
    <main>
      <header className="app-header">
        <div>
          <div className="brand">
            <Radar size={28} />
            <span>The Political Radar</span>
          </div>
          <p>Cloud sentiment intelligence for political public opinion monitoring.</p>
        </div>
        <div className="header-status">
          <AiStatus status={integrationStatus} />
          <StatusPill status={analysis?.status ?? "queued"} idle={!analysis} />
        </div>
      </header>

      <section className="layout">
        <aside className="control-panel">
          <form onSubmit={submitAnalysis} className="search-form">
            <label>
              Politician or party
              <input
                value={request.entity}
                onChange={(event) => setRequest({ ...request, entity: event.target.value })}
                minLength={2}
                required
              />
            </label>
            <label>
              Country
              <select
                value={request.country}
                onChange={(event) => setRequest({ ...request, country: event.target.value })}
                required
              >
                {countryOptions.map((country) => (
                  <option value={country} key={country}>
                    {country}
                  </option>
                ))}
              </select>
            </label>
            <div className="two-col">
              <label>
                Start date
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="DD/MM/YYYY"
                  value={dateInputs.start_date}
                  onChange={(event) => handleDateInputChange("start_date", event.target.value, setDateInputs, setRequest)}
                  required
                />
              </label>
              <label>
                End date
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="DD/MM/YYYY"
                  value={dateInputs.end_date}
                  onChange={(event) => handleDateInputChange("end_date", event.target.value, setDateInputs, setRequest)}
                  required
                />
              </label>
            </div>
            <div className="two-col">
              <label>
                Language
                <select
                  value={request.language}
                  onChange={(event) => setRequest({ ...request, language: event.target.value })}
                >
                  {languageOptions.map((language) => (
                    <option value={language.code} key={language.code}>
                      {language.code === "auto" ? language.label : `${language.label} (${language.code})`}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Limit/source
                <input
                  type="number"
                  min={5}
                  max={1000}
                  step={1}
                  value={limitInput}
                  onChange={(event) => {
                    const value = event.target.value;
                    setLimitInput(value);
                    const parsed = Number(value);
                    if (Number.isInteger(parsed) && parsed >= 5 && parsed <= 1000) {
                      setRequest({ ...request, limit_per_source: parsed });
                    }
                  }}
                />
              </label>
            </div>
            <fieldset>
              <legend>Sources</legend>
              {(["news", "youtube", "csv"] as SourceName[]).map((source) => (
                <label key={source} className="check-row">
                  <input
                    type="checkbox"
                    checked={request.sources.includes(source)}
                    onChange={() => setRequest({ ...request, sources: toggleSource(request.sources, source) })}
                  />
                  <span>{sourceLabels[source]}</span>
                </label>
              ))}
            </fieldset>
            <button type="submit" disabled={loading || request.sources.length === 0}>
              <Search size={18} />
              Run analysis
            </button>
            <label className="upload-button">
              <FileUp size={18} />
              Upload CSV
              <input type="file" accept=".csv,text/csv" onChange={uploadCsv} />
            </label>
          </form>

          {error && <p className="error">{error}</p>}

          <section className="history-panel">
            <h2>
              <History size={18} />
              History
            </h2>
            {history.length === 0 && <p className="muted">No analyses yet.</p>}
            {history.slice(0, 8).map((item) => (
              <button key={item.id} className="history-item" onClick={() => setAnalysis(item)}>
                <strong>{item.request.entity}</strong>
                <span>{item.request.country} - {item.status}</span>
              </button>
            ))}
          </section>
        </aside>

        <section className="dashboard">
          {!analysis?.aggregates && <EmptyState loading={loading || analysis?.status === "running"} />}
          {analysis?.aggregates && <Dashboard analysis={analysis} />}
        </section>
      </section>
    </main>
  );
}

function Dashboard({ analysis }: { analysis: Analysis }) {
  const aggregates = analysis.aggregates!;
  const trendChartOption = React.useMemo(() => trendOption(aggregates.daily), [aggregates.daily]);
  const distributionChartOption = React.useMemo(
    () => distributionOption(aggregates.sentiment_distribution),
    [aggregates.sentiment_distribution],
  );
  const volumeChartOption = React.useMemo(() => volumeOption(aggregates.daily), [aggregates.daily]);
  const sourceChartOption = React.useMemo(
    () => sourceOption(aggregates.source_distribution),
    [aggregates.source_distribution],
  );
  return (
    <>
      <ProfileHeader analysis={analysis} />
      {analysis.warnings?.length > 0 && <WarningPanel warnings={analysis.warnings} />}
      <section className="metric-row">
        <Metric label="Analyzed items" value={aggregates.total_items.toString()} />
        <Metric label="Positive" value={String(aggregates.sentiment_distribution.positive ?? 0)} tone="positive" />
        <Metric label="Negative" value={String(aggregates.sentiment_distribution.negative ?? 0)} tone="negative" />
        <Metric label="Detected peaks" value={aggregates.peaks.length.toString()} />
      </section>

      <section className="chart-grid">
        <ChartPanel title="Sentiment Trend" option={trendChartOption} />
        <ChartPanel title="Distribution" option={distributionChartOption} />
        <ChartPanel title="Mention Volume" option={volumeChartOption} />
        <ChartPanel title="Source Comparison" option={sourceChartOption} />
      </section>

      <section className="insight-grid">
        <Panel title="Peak Radar">
          {aggregates.peaks.length === 0 && <p className="muted">No major peaks detected.</p>}
          {aggregates.peaks.map((peak) => (
            <article className="peak" key={peak.date}>
              <strong>{formatDateForDisplay(peak.date)}</strong>
              <span>{peak.volume} mentions - {(peak.negative_share * 100).toFixed(0)}% negative</span>
              <p>{peak.note}</p>
            </article>
          ))}
        </Panel>
        <Panel title="Key Phrases">
          <div className="phrase-cloud">
            {aggregates.key_phrases.slice(0, 16).map(([phrase, count]) => (
              <span key={phrase} style={{ fontSize: `${Math.min(22, 12 + count * 2)}px` }}>
                {phrase}
              </span>
            ))}
          </div>
        </Panel>
        <Panel title="News Context">
          {aggregates.events.length === 0 && <p className="muted">Run News RSS to add event context.</p>}
          {aggregates.events.slice(0, 6).map((event) => (
            <a className="event-link" href={event.url} target="_blank" rel="noreferrer" key={`${event.date}-${event.title}`}>
              <span>{formatDateForDisplay(event.date)}</span>
              <strong>{event.title}</strong>
              <small>{event.source}</small>
            </a>
          ))}
        </Panel>
      </section>

      <section className="representatives">
        {(["positive", "neutral", "negative"] as SentimentLabel[]).map((label) => (
          <Panel title={`${label[0].toUpperCase()}${label.slice(1)} Examples`} key={label}>
            {aggregates.representatives[label]?.length === 0 && (
              <p className="muted">Run YouTube to show comment examples.</p>
            )}
            {aggregates.representatives[label]?.map((item) => (
              <blockquote key={item.id}>
                {item.text}
                <footer>{item.source.toUpperCase()} - {formatDateForDisplay(item.published_at)}</footer>
              </blockquote>
            ))}
          </Panel>
        ))}
      </section>
    </>
  );
}

function WarningPanel({ warnings }: { warnings: string[] }) {
  return (
    <section className="warning-panel">
      <strong>Data collection notice</strong>
      {warnings.map((warning) => (
        <p key={warning}>{warning}</p>
      ))}
    </section>
  );
}

function ProfileHeader({ analysis }: { analysis: Analysis }) {
  const profile = analysis.profile;
  const title = profile?.title ?? analysis.request.entity;
  const subtitle = profile?.description ?? `${analysis.request.country} political analysis`;
  return (
    <section className="profile-header">
      <div className="profile-image">
        {profile?.image_url ? <img src={profile.image_url} alt={title} /> : <Radar size={34} />}
      </div>
      <div className="profile-copy">
        <span className="profile-source">{profile ? "Wikipedia profile" : "Profile image unavailable"}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
        {profile?.extract && <p className="profile-summary">{profile.extract}</p>}
        {profile?.page_url && (
          <a href={profile.page_url} target="_blank" rel="noreferrer">
            View source
          </a>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "positive" | "negative" }) {
  return (
    <article className={`metric ${tone ?? ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function Panel({ title, children }: React.PropsWithChildren<{ title: string }>) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

const ChartPanel = React.memo(function ChartPanel({ title, option }: { title: string; option: echarts.EChartsOption }) {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const chartRef = React.useRef<echarts.ECharts | null>(null);

  React.useEffect(() => {
    if (!ref.current) return;
    chartRef.current = echarts.init(ref.current);
    const resize = () => chartRef.current?.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  React.useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return (
    <Panel title={title}>
      <div className="chart" ref={ref} />
    </Panel>
  );
});

function StatusPill({ status, idle }: { status: AnalysisStatus; idle: boolean }) {
  return <span className={`status ${idle ? "idle" : status}`}>{idle ? "Ready" : status}</span>;
}

function AiStatus({ status }: { status: IntegrationStatus | null }) {
  if (!status) {
    return <span className="ai-status">AI status unavailable</span>;
  }
  const usingAzure = status.azure_language.configured && status.azure_language.ok;
  return (
    <span className={`ai-status ${usingAzure ? "azure" : "fallback"}`} title={status.azure_language.message}>
      {usingAzure ? "Azure AI Language" : "Local AI fallback"}
    </span>
  );
}

function EmptyState({ loading }: { loading?: boolean }) {
  return (
    <section className="empty-state">
      <BarChart3 size={42} />
      <h1>{loading ? "Scanning political signals" : "Start a political sentiment scan"}</h1>
      <p>Use News RSS for live no-key data, YouTube with an API key, and CSV for the stable demo path.</p>
    </section>
  );
}

function toggleSource(sources: SourceName[], source: SourceName) {
  return sources.includes(source) ? sources.filter((item) => item !== source) : [...sources, source];
}

function trendOption(daily: DailyPoint[]): echarts.EChartsOption {
  return {
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    grid: { left: 36, right: 20, top: 20, bottom: 48 },
    xAxis: { type: "category", data: daily.map((point) => formatDateForDisplay(point.date)) },
    yAxis: { type: "value" },
    series: [
      { name: "Positive", type: "line", smooth: true, data: daily.map((point) => point.positive), color: "#1f9d62" },
      { name: "Neutral", type: "line", smooth: true, data: daily.map((point) => point.neutral), color: "#687385" },
      { name: "Negative", type: "line", smooth: true, data: daily.map((point) => point.negative), color: "#d84a4a" },
    ],
  };
}

function distributionOption(distribution: Record<SentimentLabel, number>): echarts.EChartsOption {
  const entries = Object.entries(distribution).filter(([, value]) => value > 0);
  return {
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: ["42%", "72%"],
        data: entries.map(([name, value]) => ({ name, value })),
        color: ["#1f9d62", "#8a94a6", "#d84a4a", "#c18b2d"],
      },
    ],
  };
}

function volumeOption(daily: DailyPoint[]): echarts.EChartsOption {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 36, right: 20, top: 20, bottom: 36 },
    xAxis: { type: "category", data: daily.map((point) => formatDateForDisplay(point.date)) },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: daily.map((point) => point.volume), color: "#2f6fed" }],
  };
}

function handleDateInputChange(
  field: "start_date" | "end_date",
  value: string,
  setDateInputs: React.Dispatch<React.SetStateAction<{ start_date: string; end_date: string }>>,
  setRequest: React.Dispatch<React.SetStateAction<AnalysisRequest>>,
) {
  setDateInputs((current) => ({ ...current, [field]: value }));
  const parsed = parseDisplayDate(value);
  if (parsed) {
    setRequest((current) => ({ ...current, [field]: parsed }));
  }
}

function formatDateForDisplay(value: string) {
  const isoDate = value.slice(0, 10);
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!match) return value;
  return `${match[3]}/${match[2]}/${match[1]}`;
}

function parseDisplayDate(value: string) {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value.trim());
  if (!match) return null;
  const [, day, month, year] = match;
  const parsed = new Date(Number(year), Number(month) - 1, Number(day));
  if (
    parsed.getFullYear() !== Number(year) ||
    parsed.getMonth() !== Number(month) - 1 ||
    parsed.getDate() !== Number(day)
  ) {
    return null;
  }
  return `${year}-${month}-${day}`;
}

function sourceOption(distribution: Record<SourceName, number>): echarts.EChartsOption {
  const entries = Object.entries(distribution);
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 78, right: 18, top: 20, bottom: 24 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: entries.map(([name]) => sourceLabels[name as SourceName]) },
    series: [{ type: "bar", data: entries.map(([, value]) => value), color: "#7a5cff" }],
  };
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
