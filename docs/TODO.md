# TODO Items

## 1. Core Pipeline
- [ ] Test production workflow with `scripts/run_production_pipeline.py --dry-run`
- [ ] Configure Vercel Cron Jobs for daily ingestion
- [ ] Handle edge cases (encrypted files, long email chains)

## 2. RAG Enhancement
- [ ] Configure embedding settings and index parameters
- [ ] Implement chunk-based embedding strategy
- [ ] Set up alerts for document limit
- [ ] Implement chunk-aware retrieval
- [ ] Add heading hierarchy filtering
 - [x] Enable response streaming
- [ ] Test retrieval quality improvements

## 3. Document Processing
- [ ] Complete Tesseract OCR integration
- [ ] Enhance table and column detection
- [ ] Optimize for large document batches
- [ ] Implement document type support:
  - [ ] Word documents (python-docx)
  - [ ] PowerPoint presentations (python-pptx)
  - [ ] Excel spreadsheets (openpyxl)
  - [ ] PDF documents (pypdf)

## 4. NLP Enhancement
- [ ] Implement NLTK text analysis
- [x] Optimize tokenization with tiktoken
- [ ] Enhance semantic chunking

## 5. Infrastructure
- [ ] Set up Vercel performance monitoring
- [ ] Configure API endpoints
- [ ] Implement rate limiting
- [ ] Configure MSAL authentication
- [ ] Set up secrets management
- [ ] Implement secure file handling

## 6. Testing & Validation
- [ ] Unit tests:
  - [ ] Document processing
  - [ ] Text analysis
  - [ ] Vector operations
- [ ] Integration tests:
  - [ ] End-to-end processing
  - [ ] RAG pipeline
  - [ ] Authentication flow

## 7. Performance
- [ ] Profile memory usage
- [ ] Implement streaming for large documents
- [ ] Add caching where appropriate
- [ ] Optimize document parsing