import logging
import os
from app.database.connection import PostgresConnection
from app.database.notes_queries import create_note_query
from app.services.minio_client import MinIOClientContext, save_file_to_minio
from app.services.pdf_converter import convert_to_pdf

logger = logging.getLogger(__name__)

async def process_uploaded_notes(tmp_path: str, original_filename: str, user_id: str):
    """Processes notes uploaded by the user"""
    try:
        ext = original_filename.split(".")[-1].lower()
        
        pdf_path = tmp_path
        if ext != "pdf":
            pdf_path = await convert_to_pdf(tmp_path)

        pdf_filename = os.path.basename(pdf_path)
        s3_key = f"user_uploads/{user_id}/{pdf_filename}"

        with MinIOClientContext() as s3:
            await save_file_to_minio(s3, pdf_path, s3_key)


        with PostgresConnection() as conn:
            note_id = create_note_query(
                conn=conn,
                user_id=user_id,
                title=original_filename,
                filename=original_filename,
                s3_key=s3_key
            )

        return {
            "book_metadata": None,
            "presentation_metadata": None,
            "note_metadata": {
                "type": "notes",
                "note_id": note_id,
                "title": original_filename
            }
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        logger.error(f"Error processing uploaded notes: {e}")
        raise
