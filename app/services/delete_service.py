
from app.database.book_queries import delete_book_by_id, get_book_by_id
from app.database.connection import PostgresConnection
from app.database.slides_queries import delete_slide_by_id, get_slide_by_id
from app.services.minio_client import MinIOClientContext
import os
import logging

logger = logging.getLogger(__name__)


def delete_document_and_assets(document_type: str, document_id: str, user_id: str) -> bool:
    try:
         with PostgresConnection() as conn, MinIOClientContext() as s3:
            bucket = os.getenv("MINIO_BUCKET_NAME")
            
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
                return True

            else:
                raise ValueError(f"Unsupported document type: {document_type}")
            
    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"Failed to delete document: {str(e)}")
        return False
