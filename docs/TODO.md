# TODO Items

## Ingestion Pipeline
- [X] Solidify Ingestion Pipeline
- [X] Verify connectors for Microsoft Graph (email/docs) → OneDrive → JSONL batching
- [X] Validate key attributes (author, sent_at, source) for downstream filtering and conformance with JSON schema
- [x] Ensure daily delta vs. full re-ingestion logic handles schema changes & deletions 
- [X] Integration test outlines the expected production workflow: track which files are processed, only upload new or modified ones, and handle duplicates
- [X] Write new production flow to orchestrate all modules by a scheduled job or small runner script
- [X] **DOCUMENT NAMING FIX**: Fixed temp filename issues - processed documents now use descriptive names
- [X] **ENHANCED DOCUMENT PROCESSING**: Implemented advanced text extraction with layout analysis, content cleaning, and semantic chunking
- [ ] **TEST PRODUCTION PIPELINE**: Run `scripts/run_production_pipeline.py --dry-run` to validate workflow
- [ ] **SCHEDULE PRODUCTION RUNS**: Set up cron job or Azure Functions for daily execution
- [ ] **TEST ENHANCED PROCESSING**: Run `python test_enhanced_processing.py` to validate new capabilities
- [ ] **INSTALL ADVANCED DEPENDENCIES**: Run `pip install -r requirements.txt` to get enhanced processing libraries
- [ ] Explore handling of edge cases/encrypted files
- [ ] Explore handling of long email chains

## Enhanced Document Processing ✨ NEW
- [X] **OCR & Layout Awareness**: Added pdfplumber for better PDF layout detection, OCR fallback for scanned documents
- [X] **Content Cleaning & Normalization**: Remove page numbers, headers/footers, boilerplate; fix encoding issues
- [X] **Semantic Chunking**: Intelligent document segmentation with overlapping windows (500 tokens, 75 overlap)
- [X] **Structure Preservation**: Maintain heading hierarchy and document structure in metadata
- [X] **Configurable Processing**: Full configuration support for different extraction strategies
- [ ] **OCR Implementation**: Complete Tesseract OCR integration for scanned PDFs
- [ ] **Advanced Structure Detection**: Enhance table and column detection
- [ ] **Performance Optimization**: Optimize for large document batches

## Dependency & Code Refactoring ✨ REFACTOR

### Phase 1: Dependency Cleanup
- [ ] **Switch to unstructured[pdf,docx]**: Refactor ingestion & partitioning to use the PDF+DOCX-only extra; remove all pdfplumber references
- [ ] **Eliminate pdfplumber**: Delete imports and code paths; confirm OCR fallback via pypdf + pytesseract handles scanned docs
- [ ] **Replace spaCy with tokenizers**: Remove SpaCy; integrate tokenizers for tokenization and semantic-chunk logic
- [ ] **Swap pandas for pyexcel**: Update JSONL batching, table reads/exports to use pyexcel
- [ ] **Remove unused dependencies**: Audit and remove any remaining heavy dependencies not in use

### Phase 2: Code Updates
- [ ] **Update import statements**: Replace all old library imports with new lightweight alternatives
- [ ] **Refactor processing modules**: Update `core/processing_1_2_0/` to use new dependencies
- [ ] **Update metadata extraction**: Ensure `core/graph_1_1_0/metadata_extractor.py` uses lightweight libraries
- [ ] **Test compatibility**: Verify all existing functionality works with new dependencies

### Phase 3: Infrastructure Updates  
- [ ] **Requirements & CI Updates**: Commit revised requirements.txt; update Dockerfiles, CI pipelines, and build scripts
- [ ] **Documentation updates**: Update README and docs to reflect new dependency choices
- [ ] **Performance benchmarking**: Compare before/after performance and memory usage

### Phase 4: Validation
- [ ] **Smoke-test Refactored Pipeline**: Run end-to-end ingestion and RAG tests to validate no regressions
- [ ] **Integration test suite**: Ensure all tests pass with new dependencies
- [ ] **Production validation**: Test with real data to ensure quality maintained

## Vector Store Configuration
- [ ] Confirm embedding settings (model, chunk size) and index parameters
- [ ] **UTILIZE ENHANCED CHUNKS**: Configure vector store to leverage semantic chunks from enhanced processing
- [ ] Plan for 10k–doc cap, and set alerts for when you approach limit

## Retrieval & Prompt Engineering
### RAG Endpoint & Filters
- [ ] Use your FastAPI /rag endpoint with file_search tool integration as in ADR-006
- [ ] Test attribute-filtered calls to surface only relevant segment
- [ ] **LEVERAGE CHUNK METADATA**: Utilize heading hierarchy and chunk types for better retrieval

### Prompt Templates & Context Windows
- [ ] Draft and version prompt "shells" that inject retrieved docs before the user query
- [ ] Experiment with window sizes to balance context vs. token cost
- [ ] **UTILIZE SEMANTIC CHUNKS**: Test retrieval quality with semantic vs fixed-size chunks

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
- [ ] **MONITOR PROCESSING QUALITY**: Track enhanced extraction success rates and chunk quality

### Phase 1.5: Response Streaming
- [ ] Enable and test OpenAI response streaming (ROADMAP 1.5.3) for snappier UX

### Phase 2: Observability & Incremental Updates
- [ ] Plug in Application Insights (or similar) for traces & alerts
- [ ] Design and prototype your change-detection & delta re-indexing system

### Deferred Tech Debt & Security
- [ ] Refactor auth code for separation of concerns
- [ ] Optimize vector queries, add full-stack logging, automated backups
- [ ] Implement encrypted file support, secrets management, and security logging

---

## 🎯 **IMMEDIATE NEXT STEPS**

### 1. **Test Enhanced Processing** (This Week)
```bash
# Install enhanced processing dependencies
pip install -r requirements.txt

# Test enhanced document processing
python test_enhanced_processing.py

# Test the integration workflow with enhanced processing
python -m pytest tests/integration/processing_1_2_0/test_full_workflow_integration.py -v -s

# Test the production orchestrator (dry run)
python scripts/run_production_pipeline.py --dry-run --max-items=5 --log-level=DEBUG
```

### 2. **Vector Store Configuration** (Next Priority)
- Configure chunk-based embedding strategy
- Test semantic chunks vs fixed-size chunks
- Optimize for document structure preservation

### 3. **RAG Endpoint Enhancement** (Following Week)
- Implement chunk-aware retrieval
- Add heading hierarchy filtering
- Test retrieval quality improvements