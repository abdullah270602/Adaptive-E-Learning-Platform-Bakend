import logging
import os
import traceback
import platform
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from app.auth.dependencies import get_current_user
from app.database.book_queries import (
    get_book_structure_query,
    get_books_by_user,
    get_section_content_query,
)
from app.database.connection import PostgresConnection
from app.database.notes_queries import get_notes_by_user
from app.database.slides_queries import get_slides_by_user
from app.routes.constants import NOTE_EXTENSIONS
from app.services.book_processor import parse_toc_pages
from app.services.book_upload import process_uploaded_book
from app.services.delete import delete_document_and_assets
from app.services.notes_upload import process_uploaded_notes
from app.services.presentation_upload import process_uploaded_slides
from app.services.mcq_main import process_mcq_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file", tags=["Files"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    toc_pages: str = Form(None),
    current_user: str = Depends(get_current_user),
):
    """Handles document upload and delegates to document-specific service."""
    try:
        ext = file.filename.split(".")[-1].lower()

        if document_type == "book" and ext != "pdf":
            raise HTTPException(status_code=400, detail="Books must be in PDF format.")
        elif document_type in ["slides", "presentation"] and ext != "pptx":
            raise HTTPException(status_code=400, detail="Slides must be in .pptx format.")
        elif document_type == "notes" and ext not in NOTE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Notes must be in one of these {NOTE_EXTENSIONS} formats.")

        unique_name = f"{uuid.uuid4()}_{file.filename}"
        tmp_path = os.path.join(os.getenv("TMP", "temp"), unique_name) if platform.system() == "Windows" else f"/tmp/{unique_name}"
        
        file_bytes = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)

        result = {}
        doc_id = None

        if document_type == "book":
            try:
                start_page, end_page = await parse_toc_pages(toc_pages)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

            result = await process_uploaded_book(tmp_path, file.filename, start_page, end_page, current_user)
            doc_id = result.get("book_metadata", {}).get("book_id")

        elif document_type in ["slides", "presentation"]:
            result = await process_uploaded_slides(tmp_path, file.filename, current_user)
            doc_id = result.get("presentation_metadata", {}).get("presentation_id")

        elif document_type == "notes":
            result = await process_uploaded_notes(tmp_path, file.filename, current_user)
            doc_id = result.get("note_metadata", {}).get("note_id")

        else:
            raise HTTPException(status_code=400, detail="Unsupported document type.")

        if not doc_id:
            raise HTTPException(status_code=500, detail="Document ID not found after processing.")

        # ✅ MCQ embedding logic comes AFTER all other processing
        extracted_Text = await process_mcq_document(
            tmp_path=tmp_path,
            filename=file.filename,
            user_id=current_user,
            doc_id=doc_id,
            doc_type=document_type
        )

        # ✅ Only delete temp file once everything is done
        os.remove(tmp_path)
        print("=== Final Response ===")
        print({
        "message": "Upload successful",
        **result,
        **extracted_Text})


        

        return {
            "message": "Upload successful",
            **result,
            **extracted_Text
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        logger.error(f"[Upload] Failed to upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed.")

    

    


@router.get("/books")
async def list_user_books(
    current_user: str = Depends(get_current_user),
):
    """ List all books for the current user """
    try:
        with PostgresConnection() as conn:

            books = get_books_by_user(conn, current_user)
            return {"books": books}
    except Exception as e:
        logger.error(
            f"[List Books] Error retrieving books for user {current_user}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve user books")


@router.get("/slides", status_code=status.HTTP_200_OK)
async def list_user_slides(current_user: str = Depends(get_current_user)):
    """ List all presentations for the current user """
    try:
        presentations = []
        with PostgresConnection() as conn:
            presentations = get_slides_by_user(conn, current_user)

        return {"presentations": presentations}
    
    except Exception as e:
        logging.error(f"[Slides] Failed to fetch presentations for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve presentation list")


@router.delete("/delete/{document_type}/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    document_type: str,
    document_id: str,
    current_user: str = Depends(get_current_user),
):
    """
    Deletes any document type: book, slides, notes
    """
    try:
        deleted = delete_document_and_assets(
            document_type=document_type.lower(),
            document_id=document_id,
            user_id=current_user,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail=f"{document_type.capitalize()} not found or not owned by user")

        return {"message": f"{document_type.capitalize()} deleted successfully"}

    except Exception as e:
        logging.error(f"[Delete] Failed to delete {document_type}: {e}")
        raise HTTPException(status_code=500, detail="Deletion failed.")


@router.get("/notes", status_code=status.HTTP_200_OK)
def list_user_notes(current_user: str = Depends(get_current_user)):
    try:
        with PostgresConnection() as conn:
            notes = get_notes_by_user(conn, current_user)
        return {"notes": notes}
    except Exception as e:
        logging.error(f"[List Notes] Failed to fetch notes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notes.")