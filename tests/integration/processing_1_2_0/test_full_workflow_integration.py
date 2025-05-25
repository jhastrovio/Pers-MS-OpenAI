"""
End-to-end integration test for the complete data processing workflow.
Tests the full production pipeline: track processed files, delta updates, and duplicate handling.
"""

import os
import pytest
import asyncio
import json
from datetime import datetime
from typing import Dict, List

from core.processing_1_2_0.main import DataProcessor
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.processing_1_2_0.processors.attachment_processor import AttachmentProcessor
from core.graph_1_1_0.main import GraphClient
from core.storage_1_3_0.vector_repository import VectorRepository
from core.utils.config import config, PROCESSING_CONFIG
from core.utils.onedrive_utils import list_folder_contents, load_json_file, save_json_file

LOG_PATH = "test_full_workflow_integration.log"

def log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()}: {msg}\n")

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_production_workflow():
    """
    End-to-end test that simulates the complete production workflow:
    1. Load processing state
    2. Check for new/modified files
    3. Process only delta changes
    4. Track processed items
    5. Save updated state
    6. Upload to vector store
    """
    # Clear log at start
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"Full Workflow Integration Test - {datetime.now().isoformat()}\n")

    # Verify environment
    required_vars = ['CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID', 'USER_EMAIL', 'OPENAI_API_KEY', 'OPENAI_VECTOR_STORE_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        log(f"Missing required environment variables: {', '.join(missing_vars)}")
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Initialize processors
    log("Initializing processors...")
    data_processor = DataProcessor()
    email_processor = EmailProcessor()
    document_processor = DocumentProcessor(PROCESSING_CONFIG)
    attachment_processor = AttachmentProcessor(document_processor)
    vector_repo = VectorRepository()
    graph_client = GraphClient()
    
    # Load processing state
    log("Loading processing state...")
    state_file = config["onedrive"]["file_list"]
    try:
        processing_state = await load_json_file(state_file)
        log(f"Loaded existing state with {len(processing_state.get('processed_items', {}))} processed items")
    except Exception as e:
        log(f"No existing state found, starting fresh: {str(e)}")
        processing_state = {
            "last_updated": None,
            "processed_items": {},
            "metadata": {
                "processor_version": "1.2.0",
                "test_mode": True
            }
        }

    # Track workflow statistics
    workflow_stats = {
        "emails_processed": 0,
        "documents_processed": 0,
        "attachments_processed": 0,
        "skipped_duplicates": 0,
        "new_items": 0,
        "modified_items": 0,
        "upload_success": 0,
        "upload_failures": 0
    }

    # 1. PROCESS EMAILS
    log("\n=== PROCESSING EMAILS ===")
    emails_folder = config["onedrive"]["emails_folder"]
    processed_emails_folder = config["onedrive"]["processed_emails_folder"]
    
    try:
        email_files = await list_folder_contents(emails_folder)
        eml_files = [f for f in email_files if f["name"].endswith(".eml")][:5]  # Limit for testing
        
        log(f"Found {len(eml_files)} .eml files to process")
        
        for email_file in eml_files:
            file_key = f"email:{email_file['name']}"
            file_modified = email_file.get('lastModifiedDateTime', '')
            
            # Check if already processed
            if file_key in processing_state["processed_items"]:
                last_processed = processing_state["processed_items"][file_key].get("last_modified", "")
                if last_processed == file_modified:
                    log(f"Skipping already processed email: {email_file['name']}")
                    workflow_stats["skipped_duplicates"] += 1
                    continue
                else:
                    log(f"Email modified since last processing: {email_file['name']}")
                    workflow_stats["modified_items"] += 1
            else:
                log(f"New email found: {email_file['name']}")
                workflow_stats["new_items"] += 1
            
            try:
                # Download and process email (correct API)
                eml_content = await graph_client.download_file_from_onedrive(emails_folder, email_file['name'])
                if eml_content:
                    # EmailProcessor.process() takes bytes and user_email
                    user_email = config["user"]["email"]
                    result = await email_processor.process(eml_content, user_email)
                    
                    # Update processing state
                    processing_state["processed_items"][file_key] = {
                        "file_name": email_file['name'],
                        "last_modified": file_modified,
                        "processed_at": datetime.now().isoformat(),
                        "output_file": result.get("filename"),
                        "status": "success"
                    }
                    
                    workflow_stats["emails_processed"] += 1
                    log(f"Successfully processed email: {email_file['name']} -> {result.get('filename')}")
                
            except Exception as e:
                log(f"Error processing email {email_file['name']}: {str(e)}")
                processing_state["processed_items"][file_key] = {
                    "file_name": email_file['name'],
                    "last_modified": file_modified,
                    "processed_at": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e)
                }
    
    except Exception as e:
        log(f"Error in email processing workflow: {str(e)}")

    # 2. PROCESS DOCUMENTS
    log("\n=== PROCESSING DOCUMENTS ===")
    documents_folder = config["onedrive"]["documents_folder"]
    processed_documents_folder = config["onedrive"]["processed_documents_folder"]
    
    try:
        doc_files = await list_folder_contents(documents_folder)
        allowed_exts = PROCESSING_CONFIG["ALLOWED_EXTENSIONS"]
        valid_docs = [f for f in doc_files if os.path.splitext(f["name"])[1].lower() in allowed_exts][:3]  # Limit for testing
        
        log(f"Found {len(valid_docs)} valid documents to process")
        
        for doc_file in valid_docs:
            file_key = f"document:{doc_file['name']}"
            file_modified = doc_file.get('lastModifiedDateTime', '')
            
            # Check if already processed
            if file_key in processing_state["processed_items"]:
                last_processed = processing_state["processed_items"][file_key].get("last_modified", "")
                if last_processed == file_modified:
                    log(f"Skipping already processed document: {doc_file['name']}")
                    workflow_stats["skipped_duplicates"] += 1
                    continue
                else:
                    workflow_stats["modified_items"] += 1
            else:
                workflow_stats["new_items"] += 1
            
            try:
                # Download and process document (correct API)
                content = await graph_client.download_file_from_onedrive(documents_folder, doc_file['name'])
                if content:
                    result = await document_processor._process_impl({
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
                    
                    workflow_stats["documents_processed"] += 1
                    log(f"Successfully processed document: {doc_file['name']}")
                
            except Exception as e:
                log(f"Error processing document {doc_file['name']}: {str(e)}")
                processing_state["processed_items"][file_key] = {
                    "file_name": doc_file['name'],
                    "last_modified": file_modified,
                    "processed_at": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e)
                }
    
    except Exception as e:
        log(f"Error in document processing workflow: {str(e)}")

    # 3. SAVE UPDATED STATE
    log("\n=== SAVING PROCESSING STATE ===")
    processing_state["last_updated"] = datetime.now().isoformat()
    processing_state["metadata"]["last_test_run"] = datetime.now().isoformat()
    processing_state["metadata"]["workflow_stats"] = workflow_stats
    
    try:
        await save_json_file(state_file, processing_state)
        log(f"Saved processing state with {len(processing_state['processed_items'])} items")
    except Exception as e:
        log(f"Error saving processing state: {str(e)}")

    # 4. UPLOAD TO VECTOR STORE (sample)
    log("\n=== VECTOR STORE UPLOAD ===")
    try:
        # Upload processed documents to vector store (limit to 5 for testing)
        upload_stats = await vector_repo.batch_upload(
            processed_documents_folder,
            batch_size=3,
            file_filter=lambda f: f["name"].endswith(".json")
        )
        
        workflow_stats["upload_success"] = upload_stats.get("success", 0)
        workflow_stats["upload_failures"] = upload_stats.get("failed", 0)
        log(f"Vector store upload: {upload_stats['success']} success, {upload_stats['failed']} failed")
        
    except Exception as e:
        log(f"Error in vector store upload: {str(e)}")

    # 5. FINAL REPORT
    log("\n=== WORKFLOW SUMMARY ===")
    log(f"Total emails processed: {workflow_stats['emails_processed']}")
    log(f"Total documents processed: {workflow_stats['documents_processed']}")
    log(f"Total attachments processed: {workflow_stats['attachments_processed']}")
    log(f"Skipped duplicates: {workflow_stats['skipped_duplicates']}")
    log(f"New items: {workflow_stats['new_items']}")
    log(f"Modified items: {workflow_stats['modified_items']}")
    log(f"Vector store uploads: {workflow_stats['upload_success']} success, {workflow_stats['upload_failures']} failed")

    # Assertions for test validation
    total_processed = workflow_stats["emails_processed"] + workflow_stats["documents_processed"]
    assert total_processed > 0, "No files were processed in the workflow"
    
    # Basic validation that the workflow ran
    assert workflow_stats["new_items"] + workflow_stats["modified_items"] + workflow_stats["skipped_duplicates"] > 0, "No files were found to process"
    
    # Log successful completion
    log("✅ Integration test completed successfully!")

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__]) 