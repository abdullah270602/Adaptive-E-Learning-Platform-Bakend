import subprocess
import os
import platform
import logging

logger = logging.getLogger(__name__)


async def convert_pptx_to_pdf(input_path: str) -> str:
    """
    Converts a .pptx file to .pdf using LibreOffice (cross-platform).
    """
    try:
        if not input_path.lower().endswith(".pptx"):
            raise ValueError("Only .pptx files are supported.")

        output_dir = os.path.dirname(input_path)
        filename = os.path.basename(input_path)
        pdf_filename = filename.replace(".pptx", ".pdf")
        pdf_path = os.path.join(output_dir, pdf_filename)

        # Determine correct command
        system = os.getenv("OS", None)
        if system == "Windows":
            soffice_cmd = r"C:\Program Files\LibreOffice\program\soffice.com"
        else:
            soffice_cmd = "/usr/bin/libreoffice"
            
        logger.info(f"Using LibreOffice command: {soffice_cmd}")

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
