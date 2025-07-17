
from fastapi import APIRouter, UploadFile, File, status, HTTPException
from app.services.audio_transcribe import transcribe_with_deepgram
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["Transcribe Audio"])

@router.post("", status_code=status.HTTP_200_OK)
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        transcript = await transcribe_with_deepgram(file)
        
        return {"transcript": transcript}
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")