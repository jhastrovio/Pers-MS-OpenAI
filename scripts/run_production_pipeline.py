#!/usr/bin/env python3
"""
Production Pipeline Orchestrator

This script orchestrates the complete data processing pipeline for production use:
- Processes emails, documents, and attachments with delta updates
- Tracks processing state to avoid duplicates
- Uploads processed data to vector store
- Provides comprehensive logging and error handling
- Can be run manually or scheduled (cron/Azure Functions)

Usage:
    python scripts/run_production_pipeline.py [--dry-run] [--max-items=50] [--skip-upload]
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.processing_1_2_0.main import DataProcessor
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.processing_1_2_0.processors.attachment_processor import AttachmentProcessor
from core.graph_1_1_0.main import GraphClient
from core.storage_1_3_0.vector_repository import VectorRepository
from core.utils.config import config, PROCESSING_CONFIG
from core.utils.onedrive_utils import list_folder_contents, load_json_file, save_json_file, clear_folder
from core.utils.logging import configure_logging

# Configure logging
configure_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionPipeline:
    """Production pipeline orchestrator for automated data processing."""
    
    def __init__(self, dry_run: bool = False, max_items: int = None, skip_upload: bool = False):
        """Initialize the production pipeline.
        
        Args:
            dry_run: If True, simulate operations without making changes
            max_items: Maximum number of items to process per category
            skip_upload: If True, skip vector store upload
        """
        self.dry_run = dry_run
        self.max_items = max_items
        self.skip_upload = skip_upload
        
        # Initialize processors
        self.data_processor = DataProcessor()
        self.email_processor = EmailProcessor()
        self.document_processor = DocumentProcessor(PROCESSING_CONFIG)
        self.attachment_processor = AttachmentProcessor(self.document_processor)
        self.vector_repo = VectorRepository() if not skip_upload else None
        self.graph_client = GraphClient()
        
        # Pipeline statistics
        self.stats = {
            "start_time": datetime.now(),
            "emails_processed": 0,
            "documents_processed": 0,
            "attachments_processed": 0,
            "skipped_duplicates": 0,
            "new_items": 0,
            "modified_items": 0,
            "upload_success": 0,
            "upload_failures": 0,
            "errors": []
        }
        
        logger.info(f"Production pipeline initialized (dry_run={dry_run}, max_items={max_items}, skip_upload={skip_upload})")
    
    async def load_processing_state(self) -> Dict:
        """Load the processing state from OneDrive."""
        state_file = config["onedrive"]["file_list"]
        try:
            processing_state = await load_json_file(state_file)
            logger.info(f"Loaded existing state with {len(processing_state.get('processed_items', {}))} processed items")
            return processing_state
        except Exception as e:
            logger.warning(f"No existing state found, starting fresh: {str(e)}")
            return {
                "last_updated": None,
                "processed_items": {},
                "metadata": {
                    "processor_version": "1.2.0",
                    "created_at": datetime.now().isoformat()
                }
            }
    
    async def save_processing_state(self, processing_state: Dict) -> None:
        """Save the processing state to OneDrive."""
        if self.dry_run:
            logger.info("DRY RUN: Would save processing state")
            return
        
        state_file = config["onedrive"]["file_list"]
        processing_state["last_updated"] = datetime.now().isoformat()
        
        # Convert datetime objects in stats to ISO strings for JSON serialization
        stats_copy = self.stats.copy()
        for key, value in stats_copy.items():
            if isinstance(value, datetime):
                stats_copy[key] = value.isoformat()
        
        processing_state["metadata"]["pipeline_stats"] = stats_copy
        
        try:
            await save_json_file(state_file, processing_state)
            logger.info(f"Saved processing state with {len(processing_state['processed_items'])} items")
        except Exception as e:
            logger.error(f"Error saving processing state: {str(e)}")
            self.stats["errors"].append(f"State save error: {str(e)}")
    
    async def process_emails(self, processing_state: Dict) -> None:
        """Process email files with delta updates."""
        logger.info("=== PROCESSING EMAILS ===")
        emails_folder = config["onedrive"]["emails_folder"]
        
        try:
            email_files = await list_folder_contents(emails_folder)
            eml_files = [f for f in email_files if f["name"].endswith(".eml")]
            
            if self.max_items:
                eml_files = eml_files[:self.max_items]
            
            logger.info(f"Found {len(eml_files)} .eml files to process")
            
            for email_file in eml_files:
                file_key = f"email:{email_file['name']}"
                file_modified = email_file.get('lastModifiedDateTime', '')
                
                # Check if already processed
                if file_key in processing_state["processed_items"]:
                    last_processed = processing_state["processed_items"][file_key].get("last_modified", "")
                    if last_processed == file_modified:
                        logger.debug(f"Skipping already processed email: {email_file['name']}")
                        self.stats["skipped_duplicates"] += 1
                        continue
                    else:
                        logger.info(f"Email modified since last processing: {email_file['name']}")
                        self.stats["modified_items"] += 1
                else:
                    logger.info(f"New email found: {email_file['name']}")
                    self.stats["new_items"] += 1
                
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process email {email_file['name']}")
                    continue
                
                try:
                    # Process email
                    result = await self.email_processor.process_file_from_onedrive(emails_folder, email_file['name'])
                    
                    # Update processing state
                    processing_state["processed_items"][file_key] = {
                        "file_name": email_file['name'],
                        "last_modified": file_modified,
                        "processed_at": datetime.now().isoformat(),
                        "output_file": result.get("filename"),
                        "status": "success"
                    }
                    
                    self.stats["emails_processed"] += 1
                    logger.info(f"Successfully processed email: {email_file['name']} -> {result.get('filename')}")
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_file['name']}: {str(e)}")
                    self.stats["errors"].append(f"Email processing error: {email_file['name']} - {str(e)}")
                    processing_state["processed_items"][file_key] = {
                        "file_name": email_file['name'],
                        "last_modified": file_modified,
                        "processed_at": datetime.now().isoformat(),
                        "status": "failed",
                        "error": str(e)
                    }
        
        except Exception as e:
            logger.error(f"Error in email processing workflow: {str(e)}")
            self.stats["errors"].append(f"Email workflow error: {str(e)}")
    
    async def process_documents(self, processing_state: Dict) -> None:
        """Process document files with delta updates."""
        logger.info("=== PROCESSING DOCUMENTS ===")
        documents_folder = config["onedrive"]["documents_folder"]
        
        try:
            doc_files = await list_folder_contents(documents_folder)
            allowed_exts = PROCESSING_CONFIG["ALLOWED_EXTENSIONS"]
            valid_docs = [f for f in doc_files if os.path.splitext(f["name"])[1].lower() in allowed_exts]
            
            if self.max_items:
                valid_docs = valid_docs[:self.max_items]
            
            logger.info(f"Found {len(valid_docs)} valid documents to process")
            
            for doc_file in valid_docs:
                file_key = f"document:{doc_file['name']}"
                file_modified = doc_file.get('lastModifiedDateTime', '')
                
                # Check if already processed
                if file_key in processing_state["processed_items"]:
                    last_processed = processing_state["processed_items"][file_key].get("last_modified", "")
                    if last_processed == file_modified:
                        logger.debug(f"Skipping already processed document: {doc_file['name']}")
                        self.stats["skipped_duplicates"] += 1
                        continue
                    else:
                        self.stats["modified_items"] += 1
                else:
                    self.stats["new_items"] += 1
                
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process document {doc_file['name']}")
                    continue
                
                try:
                    # Download and process document
                    content = await self.graph_client.download_file_from_onedrive(documents_folder, doc_file['name'])
                    if content:
                        result = await self.document_processor._process_impl({
                            "content": content,
                            "filename": doc_file['name'],
                            "onedrive_path": f"{documents_folder}/{doc_file['name']}"
                        })
                        
                        # Update processing state
                        processing_state["processed_items"][file_key] = {
                            "file_name": doc_file['name'],
                            "last_modified": file_modified,
                            "processed_at": datetime.now().isoformat(),
                            "output_file": result['metadata'].filename,
                            "status": "success"
                        }
                        
                        self.stats["documents_processed"] += 1
                        logger.info(f"Successfully processed document: {doc_file['name']}")
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc_file['name']}: {str(e)}")
                    self.stats["errors"].append(f"Document processing error: {doc_file['name']} - {str(e)}")
                    processing_state["processed_items"][file_key] = {
                        "file_name": doc_file['name'],
                        "last_modified": file_modified,
                        "processed_at": datetime.now().isoformat(),
                        "status": "failed",
                        "error": str(e)
                    }
        
        except Exception as e:
            logger.error(f"Error in document processing workflow: {str(e)}")
            self.stats["errors"].append(f"Document workflow error: {str(e)}")
    
    async def upload_to_vector_store(self) -> None:
        """Upload processed documents to vector store."""
        if self.skip_upload or not self.vector_repo:
            logger.info("Skipping vector store upload")
            return
        
        logger.info("=== UPLOADING TO VECTOR STORE ===")
        processed_documents_folder = config["onedrive"]["processed_documents_folder"]
        
        try:
            if self.dry_run:
                logger.info("DRY RUN: Would upload to vector store")
                return
            
            # Upload processed documents (limit batch size for production)
            upload_stats = await self.vector_repo.batch_upload(
                processed_documents_folder,
                batch_size=10,
                file_filter=lambda f: f["name"].endswith(".json")
            )
            
            self.stats["upload_success"] = upload_stats.get("success", 0)
            self.stats["upload_failures"] = upload_stats.get("failed", 0)
            logger.info(f"Vector store upload: {upload_stats['success']} success, {upload_stats['failed']} failed")
            
        except Exception as e:
            logger.error(f"Error in vector store upload: {str(e)}")
            self.stats["errors"].append(f"Vector store error: {str(e)}")
    
    async def run(self) -> Dict:
        """Run the complete production pipeline."""
        logger.info("Starting production pipeline execution")
        
        try:
            # Load processing state
            processing_state = await self.load_processing_state()
            
            # Process different file types
            await self.process_emails(processing_state)
            await self.process_documents(processing_state)
            
            # Upload to vector store
            await self.upload_to_vector_store()
            
            # Save updated state
            await self.save_processing_state(processing_state)
            
            # Generate final report
            self.stats["end_time"] = datetime.now()
            self.stats["duration"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Critical error in production pipeline: {str(e)}")
            self.stats["errors"].append(f"Critical pipeline error: {str(e)}")
            raise
    
    def print_summary(self) -> None:
        """Print a summary of the pipeline execution."""
        print("\n" + "="*60)
        print("PRODUCTION PIPELINE SUMMARY")
        print("="*60)
        print(f"Execution time: {self.stats.get('duration', 0):.2f} seconds")
        print(f"Emails processed: {self.stats['emails_processed']}")
        print(f"Documents processed: {self.stats['documents_processed']}")
        print(f"Attachments processed: {self.stats['attachments_processed']}")
        print(f"Skipped duplicates: {self.stats['skipped_duplicates']}")
        print(f"New items: {self.stats['new_items']}")
        print(f"Modified items: {self.stats['modified_items']}")
        
        if not self.skip_upload:
            print(f"Vector store uploads: {self.stats['upload_success']} success, {self.stats['upload_failures']} failed")
        
        if self.stats['errors']:
            print(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more")
        
        print("="*60)

async def main():
    """Main entry point for the production pipeline."""
    parser = argparse.ArgumentParser(description="Run the production data processing pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Simulate operations without making changes")
    parser.add_argument("--max-items", type=int, help="Maximum number of items to process per category")
    parser.add_argument("--skip-upload", action="store_true", help="Skip vector store upload")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Set logging level")
    
    args = parser.parse_args()
    
    # Configure logging level
    configure_logging(level=getattr(logging, args.log_level))
    
    # Verify environment variables
    required_vars = ['CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID', 'USER_EMAIL']
    if not args.skip_upload:
        required_vars.extend(['OPENAI_API_KEY', 'OPENAI_VECTOR_STORE_ID'])
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Run pipeline
    pipeline = ProductionPipeline(
        dry_run=args.dry_run,
        max_items=args.max_items,
        skip_upload=args.skip_upload
    )
    
    try:
        stats = await pipeline.run()
        pipeline.print_summary()
        
        # Exit with error code if there were errors
        if stats['errors']:
            sys.exit(1)
        else:
            logger.info("Production pipeline completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Production pipeline failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 