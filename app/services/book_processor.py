import re
from typing import Dict, List
from fastapi import HTTPException
import fitz  # PyMuPDF
from PIL import Image
import io, os, json
from app.database.book_queries import create_book_structure
from app.database.connection import PostgresConnection
import logging
import base64
from openai import OpenAI
from app.services.prompts import TOC_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


async def prepare_toc_images(
    pdf_path: str, start_page: int, end_page: int
) -> list[bytes]:
    """Converts PDF TOC pages to 1152x1152 images (centered) as JPEG bytes."""
    images = []

    try:
        with fitz.open(pdf_path) as doc:
            for page_num in range(start_page - 1, end_page):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Resize while preserving aspect ratio
                aspect_ratio = img.width / img.height
                target_size = (1152, 1152)

                if aspect_ratio > 1:
                    new_width = 1152
                    new_height = int(1152 / aspect_ratio)
                else:
                    new_height = 1152
                    new_width = int(1152 * aspect_ratio)

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Center on white background
                background = Image.new("RGB", target_size, (255, 255, 255))
                paste_x = (target_size[0] - new_width) // 2
                paste_y = (target_size[1] - new_height) // 2
                background.paste(img, (paste_x, paste_y))

                buf = io.BytesIO()
                background.save(buf, format="JPEG")
                images.append(buf.getvalue())

        return images

    except Exception as e:
        logger.error(f"[TOC] Failed to prepare images: {str(e)}")
        raise


def extract_text_from_pdf(pdf_path: str, start_page: int, end_page: int) -> str:
    """Extracts raw text from selected PDF pages."""
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page_num in range(start_page - 1, end_page):
                text += doc.load_page(page_num).get_text()
        return text
    except Exception as e:
        logger.error(f"[TOC] Failed to extract text from PDF: {e}")
        raise


def clean_llm_json_output(content: str) -> str:
    """Strips markdown code block ticks and leading labels like 'json'."""
    content = content.strip()
    # Remove triple backticks with optional 'json'
    content = re.sub(r"^```(json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return content.strip()


async def process_toc_with_llm(text: str) -> dict:
    """Sends TOC images to LLaMA 3.3 via Groq and returns extracted TOC structure."""
    try:
        # # Convert each image to base64
        # base64_images = [
        #     {
        #         "type": "image_url",
        #         "image_url": {
        #             "url": f"data:image/jpeg;base64,{base64.b64encode(img).decode()}"
        #         }
        #     } for img in images
        # ]

        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=os.getenv("GROQ_BASE_URL"),
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # TODO make this into a config variable
            messages=[
                {"role": "system", "content": TOC_EXTRACTION_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )

        raw_content = response.choices[0].message.content

        cleaned = clean_llm_json_output(raw_content)
        toc_structure = json.loads(cleaned)

        if isinstance(toc_structure, str):
            toc_structure = json.loads(toc_structure)

        return toc_structure

    except Exception as e:
        logger.error(f"[TOC] LLaMA TOC processing failed: {e}")
        raise



# async def create_textbook_collections(
#     file_id: str,
#     book_title: str,
#     toc_structure: List[Dict],
#     s3_key: str,
#     current_user: str,
# ) -> Dict:
#     try:
#         collections = {
#             "book_id": file_id,
#             "section_collections": [],
#             "chapter_collections": [],
#         }

#         with MinIOClientContext() as s3:
#             bucket = os.getenv("MINIO_BUCKET_NAME")

#             for chapter in toc_structure.get("chapters", []):
#                 chapter_sections = chapter.get("sections", [])
#                 chapter_page = chapter.get("page", None)
#                 chapter_title = chapter.get("title", "Untitled Chapter")
#                 chapter_number = extract_chapter_number(chapter_title)
#                 chapter_collection_id = str(uuid.uuid4())

#                 # Handle flat chapters (no sections)
#                 if not chapter_sections:
#                     chapter_sections = [{"title": chapter_title, "page": chapter_page}]

#                 section_collection_ids = []

#                 for section in chapter_sections:
#                     section_id = str(uuid.uuid4())
#                     section_collection = {
#                         "collection_id": section_id,
#                         "name": f"{book_title} - {section.get('title', 'Untitled Section')}",
#                         "created_date": datetime.now().isoformat(),
#                         "user_id": current_user,
#                         "parent_chapter": chapter_number,
#                         "materials": {
#                             "textbook_sections": [
#                                 {
#                                     "section_id": section_id,
#                                     "title": section.get("title", "Untitled Section"),
#                                     "page": section.get("page"),
#                                     "s3_key": s3_key,
#                                     "added_date": datetime.now().isoformat(),
#                                 }
#                             ],
#                             "transcriptions": [],
#                             "presentations": [],
#                             "notes": [],
#                         },
#                     }

#                     section_key = f"collections/{current_user}/{section_id}.json"
#                     s3.put_object(
#                         Bucket=bucket,
#                         Key=section_key,
#                         Body=json.dumps(section_collection).encode("utf-8"),
#                         ContentType="application/json",
#                     )

#                     section_collection_ids.append(section_id)
#                     collections["section_collections"].append(section_collection)

#                 # Chapter collection
#                 chapter_collection = {
#                     "collection_id": chapter_collection_id,
#                     "name": f"{book_title} - {chapter_number}: {chapter_title}",
#                     "created_date": datetime.now().isoformat(),
#                     "user_id": current_user,
#                     "chapter_number": chapter_number,
#                     "materials": {
#                         "textbook_sections": [
#                             {
#                                 "section_id": str(uuid.uuid4()),
#                                 "title": sec.get("title", "Untitled Section"),
#                                 "page": sec.get("page"),
#                                 "s3_key": s3_key,
#                                 "added_date": datetime.now().isoformat(),
#                             }
#                             for sec in chapter_sections
#                         ],
#                         "transcriptions": [],
#                         "presentations": [],
#                         "notes": [],
#                         "subcollections": section_collection_ids,
#                     },
#                 }

#                 chapter_key = f"collections/{current_user}/{chapter_collection_id}.json"
#                 s3.put_object(
#                     Bucket=bucket,
#                     Key=chapter_key,
#                     Body=json.dumps(chapter_collection).encode("utf-8"),
#                     ContentType="application/json",
#                 )

#                 collections["chapter_collections"].append(chapter_collection)

#         return collections

#     except Exception as e:
#         traceback.print_exc()
#         logger.error(f"[Collection] Failed to create textbook collections: {e}")
#         raise HTTPException(
#             status_code=500, detail="Failed to create textbook collections."
#         )


async def process_toc_pages(
    pdf_path: str,
    start_page: int,
    end_page: int,
    book_id: str,
    s3_key: str,
) -> dict:
    try:
        text = extract_text_from_pdf(pdf_path, start_page, end_page)
        toc_structure = await process_toc_with_llm(text)

        with PostgresConnection() as conn:
            result = create_book_structure(
                conn=conn, book_id=book_id, toc_structure=toc_structure, s3_key=s3_key
            )

        return result
    except Exception as e:
        logging.error(f"[TOC] Failed in process_toc_pages_postgres: {e}")
        raise HTTPException(status_code=500, detail="TOC processing failed.")
