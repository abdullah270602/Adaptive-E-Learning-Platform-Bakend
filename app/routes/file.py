import logging
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from app.auth.dependencies import get_current_user
from app.services.minio_client import MinIOClientContext
from app.services.textbook_processor import process_toc_pages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file", tags=["Files"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    document_type: str = Form(...),  # "textbook", "slides", "notes",
    toc_pages: str = Form(None),
    current_user: str = Depends(get_current_user)
):
    try:
        # 1. Validate and save temporarily
        ext = file.filename.split(".")[-1]
        if ext.lower() != "pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        unique_name = f"{uuid.uuid4()}_{file.filename}"
        # tmp_path = f"/tmp/{unique_name}"
        tmp_path = os.path.join(os.getenv("TMP", "temp"), unique_name)


        with open(tmp_path, "wb") as f:
            f.write(await file.read())

        # 2. Upload to MinIO
        s3_key = f"user_uploads/{current_user}/{unique_name}"
        with MinIOClientContext() as s3:
            bucket = os.getenv("MINIO_BUCKET_NAME")
            s3.upload_file(
                Filename=tmp_path,
                Bucket=bucket,
                Key=s3_key
            )

        # 3. Process if textbook + TOC
        result = None
        if document_type == "textbook" and toc_pages:
            start_page, end_page = map(int, toc_pages.split("-"))
            file_id = unique_name.split("_")[0]

            result = await process_toc_pages(
                pdf_path=tmp_path,
                start_page=start_page,
                end_page=end_page,
                file_id=file_id,
                book_title=file.filename,
                s3_key=s3_key,
                current_user=current_user
            )

        os.remove(tmp_path)

        return {
            "message": "Upload successful.",
            "s3_key": s3_key,
            "collections": result if result else None
        }

    except Exception as e:
        logger.error(f"[Upload] Failed to upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed.")
