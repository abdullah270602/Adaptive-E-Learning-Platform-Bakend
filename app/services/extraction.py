import os
import fitz  # PyMuPDF
import unicodedata
import re
from collections import Counter
import nltk

def download_nltk_resources():
    """Download required NLTK resources."""
    try:
        # Try to find the resources first
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        # Download if not found
        print("Downloading NLTK resources...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        
        nltk.download('stopwords', quiet=True)
        print("NLTK resources downloaded successfully.")

download_nltk_resources()

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize


# Download NLTK resources at module import time


# ---------- Preprocessing Helpers ----------

def normalize_unicode(text: str) -> str:
    """Normalize unicode and fix ligatures, quotes, dashes, etc."""
    text = unicodedata.normalize("NFKC", text)
    ligature_map = {
        "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
        "Œ": "OE", "œ": "oe", "æ": "ae", "Æ": "AE",
        """: "\"", """: "\"", "'": "'", "'": "'",
        "–": "-", "—": "-", "…": "...",
    }
    for wrong, right in ligature_map.items():
        text = text.replace(wrong, right)
    return text

def remove_control_characters(text: str) -> str:
    """Remove invisible or control characters."""
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C')

def clean_latex_remnants(text: str) -> str:
    """Clean up LaTeX formatting remnants and mathematical expressions."""
    # Common LaTeX patterns
    text = re.sub(r'LATEX\s*2\\"', 'LaTeX', text)
    text = re.sub(r'LATEX\s*2\\["\']', 'LaTeX', text)
    text = re.sub(r'\\([a-zA-Z]+)', r'\1', text)  # Remove backslashes from commands
    text = re.sub(r'\$([^$]+)\$', r'\1', text)  # Remove $ from inline math
    text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)  # Bold text
    text = re.sub(r'\\textit\{([^}]+)\}', r'\1', text)  # Italic text
    text = re.sub(r'\\emph\{([^}]+)\}', r'\1', text)  # Emphasized text
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)  # Generic LaTeX commands
    return text

def remove_repeated_lines(text: str, min_repeats: int = 3) -> str:
    """Remove over-repeated lines (headers, footers)."""
    lines = text.split('\n')
    counts = Counter(line.strip() for line in lines if line.strip())
    return '\n'.join(
        line for line in lines if counts[line.strip()] < min_repeats or line.strip() == ''
    )

def remove_noise_patterns(text: str) -> str:
    """Remove various noise patterns that don't add semantic value."""
    # Remove figure/table references and captions
    text = re.sub(r'(?i)(Figure|Table|Fig\.?)\s*\d+(\.\d+)*\s*[:.\-–—]?\s*.*?(?=\n|$)', '', text)
    
    # Remove page numbers and references
    text = re.sub(r'\b\d{1,4}\b(?=\s*$)', '', text, flags=re.MULTILINE)  # Standalone page numbers
    text = re.sub(r'\b(?:page|p\.)\s*\d+\b', '', text, flags=re.IGNORECASE)
    
    # Remove chapter/section number patterns when standalone
    text = re.sub(r'^\s*\d+(\.\d+)*\s*$', '', text, flags=re.MULTILINE)
    
    # Remove long digit sequences (often formatting artifacts)
    text = re.sub(r'[\d\s]{10,}', '', text)
    
    # Remove bibliography/citation patterns
    text = re.sub(r'\[\d+\]', '', text)  # [1], [23], etc.
    text = re.sub(r'\([A-Z][a-z]+\s+\d{4}\)', '', text)  # (Author 2023)
    
    return text

def clean_table_of_contents(text: str) -> str:
    """Clean up table of contents and index-like content."""
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip lines that are primarily page numbers and dots
        if re.match(r'^[.\s]*\d+\s*$', line.strip()):
            continue
        
        # Skip lines with excessive dots (table of contents leaders)
        if line.count('.') > len(line) // 4:
            continue
            
        # Clean up attached page numbers from content
        line = re.sub(r'([a-z])(\d{3,})(\d+)', r'\1. ', line)
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def fix_common_ocr_errors(text: str) -> str:
    """Fix common OCR misreads and artifacts."""
    # Common OCR substitutions
    ocr_fixes = {
        r'\bD\s*\.\s*': '= ',  # D . → =
        r'\brn\b': 'm',        # rn → m
        r'\b1\b(?=[a-z])': 'l', # 1 → l when before lowercase
        r'\b0\b(?=[a-z])': 'o', # 0 → o when before lowercase
        r'\bvv\b': 'w',        # vv → w
        r'\bII\b': 'll',       # II → ll
    }
    
    for pattern, replacement in ocr_fixes.items():
        text = re.sub(pattern, replacement, text)
    
    return text

def merge_broken_lines(text: str) -> str:
    """Merge lines that shouldn't break, preserving paragraph structure."""
    lines = text.split('\n')
    merged_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            merged_lines.append('')
            continue
            
        # If this line doesn't end with punctuation and next line doesn't start with capital,
        # it's likely a broken line
        if (i < len(lines) - 1 and 
            not re.search(r'[.!?:;]$', line) and
            lines[i + 1].strip() and
            not re.match(r'^[A-Z]', lines[i + 1].strip()) and
            not re.match(r'^\d+\.', lines[i + 1].strip())):  # Not a numbered list
            
            merged_lines.append(line + ' ')
        else:
            merged_lines.append(line)
    
    # Join and clean up extra spaces
    text = ''.join(merged_lines)
    return text

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving paragraph structure."""
    # Normalize internal whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Normalize line breaks - preserve double breaks as paragraphs
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple breaks → double break
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Clean up paragraph breaks
    text = re.sub(r'^\s+|\s+$', '', text)  # Trim start/end
    
    return text

def split_into_semantic_chunks(text: str) -> str:
    """Add clear paragraph breaks at semantic boundaries for better chunking."""
    # Add breaks before headings/subheadings
    text = re.sub(r'(\n|^)([A-Z][^.!?]*(?:Algorithm|Method|Approach|Definition|Theorem|Lemma|Proof))', r'\1\n\2', text)
    
    # Add breaks before numbered/lettered lists
    text = re.sub(r'(\n|^)(\d+\.|[a-z]\)|\([a-z]\))', r'\1\n\2', text)
    
    return text

def filter_content_for_mcq(text: str) -> str:
    """Filter out content that's not suitable for MCQ generation."""
    lines = text.split('\n')
    filtered_lines = []
    
    skip_patterns = [
        r'^(acknowledgment|preface|bibliography|index|references)',  # Front/back matter
        r'^\s*(copyright|©|\(c\))',  # Copyright notices
        r'^\s*isbn',  # ISBN numbers
        r'^\s*printed in',  # Publishing info
        r'^\s*all rights reserved',  # Rights info
    ]
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Skip lines matching exclusion patterns
        if any(re.match(pattern, line_lower) for pattern in skip_patterns):
            continue
            
        # Skip very short lines (likely fragments)
        if len(line.strip()) < 20:
            continue
            
        # Skip lines with excessive special characters
        special_char_ratio = sum(1 for c in line if not c.isalnum() and c != ' ') / max(len(line), 1)
        if special_char_ratio > 0.3:
            continue
            
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

# ---------- Enhanced Functions for Stopword Removal and Meaningful Content ----------

def download_nltk_resources():
    """Download required NLTK resources."""
    try:
        # Try to find the resources first
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        # Download if not found
        print("Downloading NLTK resources...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)  # For newer NLTK versions
        nltk.download('stopwords', quiet=True)
        print("NLTK resources downloaded successfully.")

def get_extended_stopwords() -> set:
    """Get comprehensive stopword list using NLTK and additional academic terms."""
    # NLTK resources are already downloaded at module import
    
    # Get NLTK English stopwords
    nltk_stopwords = set(stopwords.words('english'))
    
    # Additional academic and technical stopwords
    academic_stopwords = {
        'however', 'therefore', 'furthermore', 'moreover', 'nevertheless',
        'consequently', 'subsequently', 'accordingly', 'hence', 'thus',
        'particularly', 'specifically', 'generally', 'typically', 'usually',
        'often', 'sometimes', 'always', 'never', 'also', 'additionally',
        'besides', 'likewise', 'similarly', 'conversely', 'instead',
        'although', 'though', 'whereas', 'since', 'due', 'regarding',
        'concerning', 'according', 'based', 'given', 'shown', 'described',
        'presented', 'discussed', 'mentioned', 'noted', 'observed', 'found',
        'seen', 'used', 'applied', 'following', 'previous', 'next',
        'various', 'different', 'several', 'many', 'numerous', 'multiple',
        'certain', 'particular', 'important', 'significant', 'possible',
        'likely', 'probably', 'perhaps', 'maybe', 'clearly', 'obviously'
    }
    
    return nltk_stopwords | academic_stopwords

def remove_stopwords_from_text(text: str) -> str:
    """Remove stopwords using NLTK while preserving meaningful content and structure."""
    # NLTK resources are already downloaded at module import
    stop_words = get_extended_stopwords()
    
    # Split into paragraphs to preserve structure
    paragraphs = text.split('\n\n')
    cleaned_paragraphs = []
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            cleaned_paragraphs.append('')
            continue
            
        # Tokenize into sentences
        sentences = sent_tokenize(paragraph)
        cleaned_sentences = []
        
        for sentence in sentences:
            # Tokenize words
            words = word_tokenize(sentence)
            
            # Filter out stopwords and short words
            meaningful_words = [
                word for word in words 
                if word.lower() not in stop_words 
                and len(word) > 2 
                and word.isalpha()  # Only alphabetic words
            ]
            
            # Only keep sentences with sufficient meaningful content
            if len(meaningful_words) >= 3:
                filtered_sentence = ' '.join(meaningful_words)
                if filtered_sentence:
                    cleaned_sentences.append(filtered_sentence)
        
        if cleaned_sentences:
            cleaned_paragraphs.append('. '.join(cleaned_sentences) + '.')
    
    return '\n\n'.join(cleaned_paragraphs)

def extract_technical_terms(text: str) -> set:
    """Extract technical terms and domain-specific vocabulary."""
    # Patterns for technical terms
    technical_patterns = [
        r'\b[A-Z][a-z]+(?:[A-Z][a-z]*)+\b',  # CamelCase terms
        r'\b[a-z]+(?:-[a-z]+)+\b',           # hyphenated terms
        r'\b\w*(?:algorithm|method|function|process|system|structure|model|theory|principle)\w*\b',
        r'\b\w*(?:analysis|synthesis|optimization|implementation|framework|architecture)\w*\b',
        r'\b[A-Z]{2,}\b',                    # Acronyms
    ]
    
    technical_terms = set()
    for pattern in technical_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        technical_terms.update(matches)
    
    return technical_terms

def enhance_meaningful_content(text: str) -> str:
    """Enhanced content extraction focusing on meaningful academic/technical content."""
    # NLTK resources are already downloaded at module import
    
    # Remove very short paragraphs (likely fragments)
    paragraphs = text.split('\n\n')
    meaningful_paragraphs = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Skip paragraphs that are too short or have low information density
        if len(paragraph) < 50:
            continue
            
        # Calculate word density (meaningful words vs total words)
        words = word_tokenize(paragraph.lower())
        stop_words = get_extended_stopwords()
        meaningful_word_count = sum(1 for word in words if word not in stop_words and len(word) > 2)
        
        if len(words) > 0 and meaningful_word_count / len(words) > 0.3:  # At least 30% meaningful words
            meaningful_paragraphs.append(paragraph)
    
    return '\n\n'.join(meaningful_paragraphs)

def extract_key_concepts(text: str) -> list:
    """Extract key concepts and important terms for MCQ generation."""
    # NLTK resources are already downloaded at module import
    
    # Tokenize and clean
    words = word_tokenize(text.lower())
    stop_words = get_extended_stopwords()
    
    # Filter meaningful words
    meaningful_words = [
        word for word in words 
        if word not in stop_words 
        and len(word) > 3 
        and word.isalpha()
    ]
    
    # Count frequency
    word_freq = Counter(meaningful_words)
    
    # Extract technical terms
    technical_terms = extract_technical_terms(text)
    
    # Combine and prioritize
    key_concepts = []
    
    # Add high-frequency meaningful words
    for word, freq in word_freq.most_common(50):
        if freq > 2:  # Appears at least 3 times
            key_concepts.append(word)
    
    # Add technical terms
    key_concepts.extend(list(technical_terms))
    
    return list(set(key_concepts))  # Remove duplicates

def preprocess_text_for_vector_store(text: str) -> str:
    """Specialized preprocessing for vector store with enhanced stopword removal."""
    # Basic cleaning
    text = normalize_unicode(text)
    text = remove_control_characters(text)
    text = clean_latex_remnants(text)
    text = fix_common_ocr_errors(text)
    text = remove_noise_patterns(text)
    text = clean_table_of_contents(text)
    text = remove_repeated_lines(text)
    text = merge_broken_lines(text)
    
    # Enhanced processing for vector storage
    text = enhance_meaningful_content(text)
    text = remove_stopwords_from_text(text)
    text = normalize_whitespace(text)
    
    return text

# ---------- Original Pipeline Functions ----------

def preprocess_text_for_rag(text: str) -> str:
    """Run full preprocessing pipeline optimized for RAG-based MCQ generation."""
    text = normalize_unicode(text)
    text = remove_control_characters(text)
    text = clean_latex_remnants(text)
    text = fix_common_ocr_errors(text)
    text = remove_noise_patterns(text)
    text = clean_table_of_contents(text)
    text = remove_repeated_lines(text)
    text = merge_broken_lines(text)
    text = split_into_semantic_chunks(text)
    text = normalize_whitespace(text)
    text = filter_content_for_mcq(text)
    text = enhance_meaningful_content(text)  # Enhanced content filtering
    text = remove_stopwords_from_text(text)  # Remove stopwords using NLTK
    return text

# ---------- Main Extraction Function ----------

async def extract_and_preprocess_text(file_path: str, extension: str) -> str:
    """Extract and clean text from supported file types for RAG MCQ generation."""
    try:
        doc = fitz.open(file_path)
        raw_text = "".join(page.get_text() for page in doc)
        clean_text = preprocess_text_for_rag(raw_text)
        return clean_text
    except Exception as e:
        raise RuntimeError(f"Text extraction failed: {str(e)}")
    finally:
        if 'doc' in locals():
            doc.close()