import subprocess
import os
import logging
import platform

from app.services.constants import LINUX_SOFFICE_PATH, WINDOWS_SOFFICE_PATH

logger = logging.getLogger(__name__)


def get_soffice_cmd() -> str:
    """ Returns the path to the LibreOffice CLI """
    system = platform.system()
    
    if system == "Windows":
        return WINDOWS_SOFFICE_PATH
    elif system == "Linux":
        return LINUX_SOFFICE_PATH
    else:
        raise NotImplementedError(f"Unsupported OS: {system}")



async def convert_to_pdf(input_path: str) -> str:
    """
    Converts supported file types (.pptx, .docx, .txt, etc.) to .pdf using LibreOffice CLI.
    """
    try:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        output_dir = os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        # Determine correct command
        soffice_cmd = get_soffice_cmd()

        logger.info(f"Starting conversion: {input_path.split(".")[-1].upper()} to PDF")

        command = [
            soffice_cmd,
            "--headless",
            "--convert-to",
            "pdf",
            input_path,
            "--outdir",
            output_dir,
        ]

        logger.info(f"Running LibreOffice command: {' '.join(command)}")

        result = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        

        if not os.path.exists(pdf_path):
            logger.error("PDF file not created. Output:")
            logger.error(result.stdout.decode())
            logger.error(result.stderr.decode())
            raise FileNotFoundError(f"Expected output file not found: {pdf_path}")

        logger.info(f"PDF conversion successful: {pdf_path}")
        return pdf_path

    except subprocess.CalledProcessError as e:
        logger.error(f"LibreOffice failed:\n{e.stderr.decode()}")
        raise RuntimeError(f"LibreOffice conversion failed: {e.stderr.decode()}")
    except Exception as e:
        logger.error(f"Unhandled error during conversion: {e}")
        raise

