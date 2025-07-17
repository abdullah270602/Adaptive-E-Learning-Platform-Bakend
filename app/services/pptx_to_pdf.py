import subprocess
import os
import logging

logger = logging.getLogger(__name__)


async def convert_pptx_to_pdf(input_path: str) -> str:
    """ 
    Converts a PowerPoint .pptx file to .pdf using LibreOffice CLI. 
    Returns the path to the converted PDF. 
    """
    try:
        if not input_path.lower().endswith(".pptx"):
            raise ValueError("File must be a .pptx")

        output_dir = os.path.dirname(input_path)
        
        is_windows = os.getenv("OS", None) == "Windows"
        soffice_cmd = (
            r"C:\Program Files\LibreOffice\program\soffice.com"
            if is_windows
            else "/usr/bin/libreoffice"
        )

        try:
            logger.info(f"Converting {input_path} to PDF using LibreOffice CLI")
            subprocess.run(
                [soffice_cmd, "--headless", "--convert-to", "pdf", input_path, "--outdir", output_dir],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        except FileNotFoundError:
            raise RuntimeError(f"{soffice_cmd} not found. Make sure LibreOffice is installed.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"{soffice_cmd} conversion failed: {e.stderr.decode()}")

        pdf_path = os.path.join(output_dir, os.path.basename(input_path).replace(".pptx", ".pdf"))
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Conversion failed: PDF not found at {pdf_path}")
        
        logger.info(f"Converted PPTX to PDF successfully: {pdf_path}")
        return pdf_path

    except Exception as e:
        import traceback; traceback.print_exc();
        logger.error(f"Error converting PPTX to PDF: {e}")
        raise