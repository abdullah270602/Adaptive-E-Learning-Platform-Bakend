import logging
import os
import uuid
from app.database.book_queries import create_book_query
from app.database.connection import PostgresConnection
from app.services.book_processor import process_toc_pages
from app.services.minio_client import MinIOClientContext, save_file_to_minio

logger = logging.getLogger(__name__)

async def process_uploaded_book(tmp_path: str, original_filename: str, toc_pages: str, user_id: str):
    """ Processes a book uploaded by the user """
    try:
        book_id = str(uuid.uuid4())
        s3_key = f"user_uploads/{user_id}/{os.path.basename(tmp_path)}"

        with MinIOClientContext() as s3:
            await save_file_to_minio(s3, tmp_path, s3_key)
            

        with PostgresConnection() as conn:
            create_book_query(conn, user_id, book_id, original_filename, original_filename, s3_key)

        metadata = None
        if toc_pages:
            start_page, end_page = map(int, toc_pages.split("-"))
            metadata = await process_toc_pages(
                pdf_path=tmp_path,
                start_page=start_page,
                end_page=end_page,
                book_id=book_id,
                s3_key=s3_key,
            )
            metadata["type"] = "book"
            metadata["title"] = original_filename
            
            metadata.pop("section_collections") # FIXME remove this from the query it self
            metadata.pop("chapter_collections") # FIXME remove this from the query it self

        return {
            "book_metadata": metadata,
            "presentation_metadata": None,
            "note_metadata": None,
        }
    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"Error processing uploaded book: {e}")
        raise
