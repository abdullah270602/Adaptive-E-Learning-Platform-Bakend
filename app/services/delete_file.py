from app.cache.metadata import delete_cached_doc_metadata
from app.database.book_queries import delete_book_by_id, get_book_by_id
from app.database.connection import PostgresConnection
from app.database.notes_queries import delete_note_by_id, get_note_by_id
from app.database.slides_queries import delete_slide_by_id, get_slide_by_id
from app.database.study_mode_queries import delete_all_document_data
from app.services.minio_client import MinIOClientContext
from app.services.vector_storage import delete_document_embeddings  # Adjust path as needed
import os
import logging

logger = logging.getLogger(__name__)


def delete_document_and_assets(document_type: str, document_id: str, user_id: str) -> bool:
    try:
        with PostgresConnection() as conn, MinIOClientContext() as s3:
            bucket = os.getenv("MINIO_BUCKET_NAME")
            
            # Delete all related study mode data (chats, progress, tool responses)
            try:
                deletion_stats = delete_all_document_data(conn, document_id, user_id, document_type)
                logger.info(f"Deleted study mode data for {document_id}: {deletion_stats}")
            except Exception as e:
                logger.warning(f"Failed to delete study mode data for {document_id}: {e}")
                # Continue with document deletion even if study mode data deletion fails
            
            # Delete cached metadata
            try:
                cache_deleted = delete_cached_doc_metadata(document_id, document_type)
                logger.info(f"Cache deletion attempted for {document_id}: {cache_deleted}")
            except Exception as e:
                logger.warning(f"Failed to delete cache for {document_id}: {e}")
                # Continue with document deletion even if cache deletion fails
            
            # Delete embeddings from vector database
            try:
                vector_deletion_result = delete_document_embeddings(user_id, document_id)
                if vector_deletion_result["status"] == "success":
                    logger.info(f"Successfully deleted embeddings for {document_id}: {vector_deletion_result}")
                elif vector_deletion_result["status"] == "warning":
                    logger.warning(f"Vector deletion warning for {document_id}: {vector_deletion_result['message']}")
                else:
                    logger.error(f"Failed to delete embeddings for {document_id}: {vector_deletion_result['message']}")
            except Exception as e:
                logger.warning(f"Failed to delete embeddings for {document_id}: {e}")
                # Continue with document deletion even if vector deletion fails
            
            # Delete the actual document and its S3 assets
            if document_type == "book":
                book = get_book_by_id(conn, document_id, user_id)
                if not book:
                    return False
                
                delete_book_by_id(conn, document_id, user_id)
                s3.delete_object(Bucket=bucket, Key=book["s3_key"])
                return True
            
            elif document_type == "presentation":
                slide = get_slide_by_id(conn, document_id, user_id)
                if not slide:
                    return False
                
                delete_slide_by_id(conn, document_id, user_id)
                s3.delete_object(Bucket=bucket, Key=slide["s3_key"])
                return True
            
            elif document_type == "notes":
                note = get_note_by_id(conn, document_id, user_id)
                if not note:
                    return False
                delete_note_by_id(conn, document_id, user_id)
                s3.delete_object(Bucket=bucket, Key=note["s3_key"])
                
                return True
            
            else:
                raise ValueError(f"Unsupported document type: {document_type}")
                
    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"Failed to delete document: {str(e)}")
        return False