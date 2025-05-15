# Pers MS OpenAI – Project Roadmap

Version: 1.0 – 14 May 2025

## 📋 Project Overview

This roadmap tracks the implementation status and future work for the Pers MS OpenAI platform, following the architecture defined in `design_decisions.md`.

## 🎯 Phase 1: Core Infrastructure (Current)

### Data Ingestion Pipeline
- [ ] 1.1.0: Microsoft Graph Integration
  - [ ] 1.1.1: Email extraction service
  - [ ] 1.1.2: OneDrive document sync
  - [ ] 1.1.3: MSAL authentication setup

- [ ] 1.2.0: Data Processing
  - [ ] 1.2.1: Email cleaning & enrichment
  - [ ] 1.2.2: Document text extraction
  - [ ] 1.2.3: Attachment processing

- [ ] 1.3.0: Storage Layer
  - [ ] 1.3.1: OneDrive folder structure setup
  - [ ] 1.3.2: JSON schema implementation
  - [ ] 1.3.3: JSONL batch processing

### API & Vector Store
- [ ] 1.4.0: FastAPI Backend
  - [ ] 1.4.1: Health check endpoints
  - [ ] 1.4.2: RAG endpoint implementation
  - [ ] 1.4.3: Error handling & logging

- [ ] 1.5.0: OpenAI Integration
  - [ ] 1.5.1: Vector store setup
  - [ ] 1.5.2: Attribute filtering
  - [ ] 1.5.3: Response streaming

## 🎯 Phase 2: Enhancement & Scale

### Performance & Monitoring
- [ ] 2.1.0: Observability
  - [ ] 2.1.1: Application Insights integration
  - [ ] 2.1.2: Custom metrics & alerts
  - [ ] 2.1.3: Performance monitoring

### Data Management
- [ ] 2.2.0: Incremental Updates
  - [ ] 2.2.1: Change detection system
  - [ ] 2.2.2: Delta processing
  - [ ] 2.2.3: Re-indexing capability

## 📁 File Organization

### Code Structure
```
core/
├── 1.1.0-graph/           # Microsoft Graph integration
├── 1.2.0-processing/      # Data processing services
├── 1.3.0-storage/         # Storage layer implementation
├── 1.4.0-api/            # FastAPI backend
└── 1.5.0-openai/         # OpenAI integration
```

### Data Structure
```
data/
├── 1.1.0-raw/            # Raw data from Graph
├── 1.2.0-processed/      # Cleaned & enriched data
├── 1.3.0-storage/        # OneDrive sync files
└── 1.5.0-vector/         # Vector store data
```

## 📊 Progress Tracking

| Phase | Component | Status | Target Date |
|-------|-----------|---------|-------------|
| 1     | Graph Integration | Not Started | TBD |
| 1     | Data Processing | Not Started | TBD |
| 1     | Storage Layer | Not Started | TBD |
| 1     | API & Vector Store | Not Started | TBD |

## 🔄 Version Control

- Each component follows semantic versioning (X.Y.Z)
- Major version (X): Phase number
- Minor version (Y): Component number
- Patch version (Z): Implementation iteration

## 📝 Notes

- All code should include unit tests and documentation
- Each component should be independently deployable
- Monitor vector store usage to stay within 10k document limit
- Regular backups of OneDrive data required