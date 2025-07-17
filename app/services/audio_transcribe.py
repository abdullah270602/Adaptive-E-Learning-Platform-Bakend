import aiohttp
import tempfile
import os
import logging
from fastapi import UploadFile, HTTPException, status

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "audio/mpeg", "audio/mp3", "video/mp4", "video/mpeg",
    "audio/x-m4a", "audio/wav", "audio/webm", "audio/ogg", "audio/flac"
}


async def transcribe_with_deepgram(file: UploadFile) -> str:
    """ Transcribe audio file using Deepgram API."""
    
    # if file.content_type not in ALLOWED_CONTENT_TYPES:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
    #     )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        headers = {
            "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
            "Content-Type": file.content_type
        }

        with open(tmp_path, "rb") as f:
            audio_data = f.read()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepgram.com/v1/listen",
                data=audio_data,
                headers=headers
            ) as resp:
                logger.info(f"Deepgram response: {resp.status}")
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail="Transcription failed")

                result = await resp.json()
                transcript = (
                    result.get("results", {})
                          .get("channels", [{}])[0]
                          .get("alternatives", [{}])[0]
                          .get("transcript", "")
                )

        return transcript

    except Exception as e:
        logger.exception("Error in Deepgram transcription")
        raise HTTPException(status_code=500, detail="Transcription service failed")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
