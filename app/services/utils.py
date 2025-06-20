import re


def extract_chapter_number(title: str) -> str:
    """ Extracts the chapter number from a given title string. """
    match = re.search(r"Chapter\s+(\d+)", title, re.IGNORECASE)
    return match.group(1) if match else "N/A"