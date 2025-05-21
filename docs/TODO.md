# TODO Items

## Ingestion Pipeline
- [ ] Solidify Ingestion Pipeline
- [ ] Verify connectors for Microsoft Graph (email/docs) → OneDrive → JSONL batching
- [ ] Validate key attributes (author, sent_at, source) for downstream filtering and conformance with JSON schema
- [ ] Ensure daily delta vs. full re-ingestion logic handles schema changes & deletions 
- [ ] Integration test outlines the expected production workflow: track which files are processed, only upload new or modified ones, and handle duplicates
- [ ] Write new production flow to orchestrate all modules by a scheduled job or small runner script
- [ ] Explore handling of edge cases/encrypted files
- [ ] Explore handling of long email chains

## Vector Store Configuration
- [ ] Confirm embedding settings (model, chunk size) and index parameters
- [ ] Plan for 10k–doc cap, and set alerts for when you approach limit

## Retrieval & Prompt Engineering
### RAG Endpoint & Filters
- [ ] Use your FastAPI /rag endpoint with file_search tool integration as in ADR-006
- [ ] Test attribute-filtered calls to surface only relevant segment

### Prompt Templates & Context Windows
- [ ] Draft and version prompt "shells" that inject retrieved docs before the user query
- [ ] Experiment with window sizes to balance context vs. token cost

### Response Schema & QA Testing
- [ ] Enforce { answer, citations[], confidence } structure on every response
- [ ] Build automated tests to check for hallucinations, completeness, and citation accuracy
- [ ] Develop evals framework

## Lightweight UI & Access
### Minimal Chat Interface
- [ ] Embed ChatGPT Responses API calls directly in a simple HTML/CLI/Slack bot—no heavy front-end
- [ ] Leverage streaming once enabled to give near-real-time feedback (see Phase 1.5.3 below)

### Internal Auth & Permissions
- [ ] Integrate MSAL client-credential flow so only you and your partners can query the pipeline

## Metrics, Monitoring & Later Enhancements
### Immediate Metrics Instrumentation
- [ ] Track retrieval latency, token usage, answer precision/recall, and error rates

### Phase 1.5: Response Streaming
- [ ] Enable and test OpenAI response streaming (ROADMAP 1.5.3) for snappier UX

### Phase 2: Observability & Incremental Updates
- [ ] Plug in Application Insights (or similar) for traces & alerts
- [ ] Design and prototype your change-detection & delta re-indexing system

### Deferred Tech Debt & Security
- [ ] Refactor auth code for separation of concerns
- [ ] Optimize vector queries, add full-stack logging, automated backups
- [ ] Implement encrypted file support, secrets management, and security logging 