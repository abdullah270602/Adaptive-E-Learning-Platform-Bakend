TOC_EXTRACTION_PROMPT = """
You are an expert at extracting Table of Contents (TOC) information from a extracted text.

TASK: Analyze the provided text and extract the hierarchical structure of chapters and sections.
The text is from a textbook or academic document. Prioritize interpreting structured educational hierarchies.

INSTRUCTIONS:
1. Identify all chapter titles and their corresponding sections
2. For each chapter:
   - "title" should include the full chapter title (e.g., "Chapter 1: Introduction to Physics")
   - "page" should be the integer page number from the right column
3. Convert Roman numerals (I, II, III, etc) to regular numbers in the chapter titles
4. Include the Prologue as a chapter with title "Prologue"
5. Make sure all page numbers are integers
6. Do not include any explanatory text in your response, only the JSON object
7. Maintain the hierarchical order as shown in the original TOC
8. Include page numbers if visible (use null if not visible)
9. Focus on two levels: chapters and their main sections only
10. Clean up formatting artifacts (extra spaces, special characters, etc.)
11. If multiple TOC pages are provided, combine them into a single structure

OUTPUT FORMAT: Return ONLY valid JSON in this exact format:
{
  "chapters": [
    {
      "title": "Chapter 1: Introduction to Physics",
      "page": 1,
      "sections": [
        {
          "title": "1.1 What is Physics?",
          "page": 2
        },
        {
          "title": "1.2 Basic Concepts",
          "page": 8
        }
      ]
    },
    {
      "title": "Prologue",
      "page": null,
      "sections": []
    }
  ]
}

IMPORTANT RULES:
- Return ONLY the JSON object, no additional text or explanations
- Use "page": null if page numbers are not visible or unclear
- Use empty arrays [] for sections if none exist
- Preserve original numbering schemes in section titles (1.1, A.1, etc.)
- If text is unclear or cut off, use your best judgment but indicate uncertainty with [?]
- Handle common TOC formats: numbered chapters, lettered sections, indented hierarchies

QUALITY CHECKS:
- Ensure all opening/closing braces and brackets match
- Verify all strings are properly quoted
- Check that commas separate array elements correctly
- Validate the JSON structure before returning
"""