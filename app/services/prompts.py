import json

from app.schemas.learning_profile_form import LEARNING_PROFILE_FORM


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

LEARNING_PROFILE_SYSTEM_PROMPT = """ 
You are a learning style analyst that specializes in creating personalized VRK (Visual, Reading/Writing, Kinesthetic) learning profile descriptions. Your role is to:

1. Analyze questionnaire responses that measure learning preferences across visual, reading/writing, and kinesthetic modalities
2. Generate detailed, actionable learning profiles in paragraph form
3. Integrate behavioral preferences (timing, environment, goals) with learning style data
4. Write in second person ("You prefer...") to make insights immediately applicable
5. Provide specific, practical recommendations rather than generic statements

Your descriptions should be 150-200 words, professionally written but personal in tone, and focus on how the individual actually learns best rather than just listing their preferences.
"""

def get_learniing_style_prompt( answers, vrk_scores, dominant_styles, behavioral_prefs):
    
    LEARNING_STYLE_PROMPT = f"""You are analyzing results from a VRK learning style assessment combined with behavioral preferences. Generate a comprehensive, personalized description of the user's learning style.

    **ASSESSMENT CONTEXT:**
    This combines VRK learning modalities (Visual, Reading/Writing, Kinesthetic) with behavioral factors like timing, environment, and goals.

    **RAW DATA:**
    Questionnaire Structure:
    {LEARNING_PROFILE_FORM}

    User Responses:
    {json.dumps(answers, indent=2)}

    **CALCULATED INSIGHTS:**
    VRK Scores: {json.dumps(vrk_scores, indent=2)}
    Dominant Learning Style(s): {dominant_styles}
    Behavioral Preferences: {json.dumps(behavioral_prefs, indent=2)}

    **OUTPUT REQUIREMENTS:**
    Create a single, flowing paragraph (150-200 words) that:

    1. **Identifies Primary Style**: Start with their dominant learning preference based on highest VRK scores
    2. **Describes Processing Style**: Explain HOW they best absorb and retain information
    3. **Integrates Behavioral Context**: Weave in their timing, environment, and goal preferences
    4. **Provides Specific Insights**: Give concrete, actionable understanding of their learning approach
    5. **Addresses Secondary Preferences**: Mention other strong areas or balanced tendencies

    **WRITING GUIDELINES:**
    - Use second person ("You demonstrate..." "Your preference for...")
    - Professional yet personal tone
    - Avoid generic educational jargon
    - Focus on practical implications
    - Single paragraph, no bullet points or lists
    - Response should only contain the learning style description, no additional text

    **SPECIAL HANDLING:**
    - If scores are close (within 2 points): Describe as "balanced" or "multimodal"
    - If one style is very low (≤4): Briefly mention what to avoid
    - If behavioral preferences seem to conflict with learning style: Address constructively

    **EXAMPLE TONE:**
    "You exhibit a strong kinesthetic learning preference, demonstrating highest engagement when you can physically interact with material through hands-on activities and real-world problem solving. Your preference for evening study sessions with background music creates an environment that supports your need for dynamic, active learning experiences..."

    Generate the learning style description now:"""
    
    return LEARNING_STYLE_PROMPT