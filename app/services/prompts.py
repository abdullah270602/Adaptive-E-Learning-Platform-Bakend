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


def get_learniing_style_prompt(answers, vrk_scores, dominant_styles, behavioral_prefs):

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


DIAGRAM_GENERATION_PROMPT = """
You are an expert at creating clear, educational diagrams using mermaid syntax. Your task is to generate 2-3 simple Mermaid flowcharts showing the main concepts from this content.

**BOOK**: {book_name}
**CHAPTER**: {chapter_name}  
**SECTION**: {section_name}

**CONTENT** the page currently viewing :
{content}


**LEARNER PROFILE**:
{learning_profile}

**RULES**:
- Use only: graph TD, [square brackets], and -->
- Max 10 nodes per diagram
- Keep labels short (1-4 words) but MEANINGFUL
- Extract SPECIFIC terms, formulas, and concepts from the content
- Show logical relationships: causes → effects, steps → outcomes, parts → wholes
- Each diagram should focus on a different aspect of the topic
- Use actual terminology from the content, not generic words
- Avoid spaces in compound labels (use "RightTriangle" not "Right Triangle")

**CONTEXT-AWARE FOCUS**:
- Consider the book/chapter/section context for relevance
- Prioritize concepts that fit within this specific learning sequence
- Connect to broader chapter themes where appropriate
- Adapt complexity to the learner's profile

**DIAGRAM TYPES TO FOCUS ON**:
1. **Process Flow**: Show how something works step-by-step
2. **Cause-Effect**: Show what leads to what and why
3. **System Structure**: Show how components relate to each other
4. **Concept Hierarchy**: Show how ideas build on each other

**QUALITY CHECKS**:
- Can someone understand the topic just from your diagrams?
- Do your node labels come directly from the content?
- Are you showing real relationships, not just random connections?
- Does each diagram reveal something different about the topic?
- Would these diagrams help someone study or remember the concepts?

**THINK BEFORE CREATING**:
1. What are the key processes described?
2. What causes what in this content?
3. How do the components interact?
4. What would be most helpful for understanding?

EXAMPLES OF GOOD vs BAD DIAGRAMS:

## GOOD EXAMPLES:

**Content**: "Photosynthesis converts sunlight, CO2, and water into glucose and oxygen through light reactions in thylakoids and Calvin cycle in stroma."

graph TD
    Sunlight --> Chlorophyll
    CO2 --> CalvinCycle
    H2O --> LightReactions
    Chlorophyll --> LightReactions
    LightReactions --> ATP
    LightReactions --> NADPH
    ATP --> CalvinCycle
    NADPH --> CalvinCycle
    CalvinCycle --> Glucose

**Why good**: Shows actual process flow with specific molecules and locations.

**Content**: "Supply increases when price rises. Demand decreases when price rises. Market equilibrium occurs where they intersect."

graph TD
    PriceIncrease --> SupplyIncrease
    PriceIncrease --> DemandDecrease
    SupplyIncrease --> MarketEquilibrium
    DemandDecrease --> MarketEquilibrium
    MarketEquilibrium --> FinalPrice

**Why good**: Shows the dynamic relationship and feedback loops.

## BAD EXAMPLES TO AVOID:

**Bad**: Linear text-following

```mermaid
graph TD
    Mitosis --> Prophase
    Prophase --> Metaphase
    Metaphase --> Anaphase
**Why bad**: Just follows text order, doesn't show WHY or HOW.

**Bad**: Generic concepts
```mermaid
graph TD
    Process --> Step1
    Step1 --> Step2
    Step2 --> Result
**Why bad**: No specific terminology, could apply to anything.

**Bad**: No real relationships
```mermaid
graph TD
    Topic --> Concept1
    Topic --> Concept2
    Topic --> Concept3
**Why bad**: Just lists items, shows no meaningful connections.

CRITICAL: Return ONLY Mermaid diagrams. No explanations, no other text, no introductions.

## OUTPUT FORMAT (STRICT):

```mermaid
graph TD
    A[Main Concept] --> B[Related Idea]
    B --> C[Result]
"""


GAME_IDEA_PROMPT = """
You are an educational game designer tasked with creating an interactive learning game concept. This concept will later be implemented by another AI as a React-based web application.
## Your Task
Analyze the provided educational materials and user learning profile, then design ONE specific game concept that reinforces the key learning objectives.
Required Inputs Analysis
## 1. Content Analysis
From the primary content provided below, identify:

Key concepts: What are the 2-3 most important concepts students should learn?
Learning objectives: What should students be able to do after engaging with this content?
Difficulty level: Is this beginner, intermediate, or advanced material?

## Primary Content:
{content}
## 2. Learning Profile Analysis
Based on the user's learning profile below, determine:

Preferred learning style (visual, auditory, kinesthetic, reading/writing)
Engagement preferences (competitive, collaborative, exploratory, structured)
Skill level and background

## User Learning Profile:
{learning_profile}
Game Design Requirements
Your game concept must meet ALL of these criteria:

Technical: Implementable as a React component with basic JavaScript
Educational: Directly reinforces 1-3 key concepts from the materials
Accessible: Runs smoothly in web browsers without heavy resources
Engaging: Appropriate challenge level with clear feedback mechanisms
Personalized: Matches the user's learning style and preferences

Required Output Format
Provide your game concept in this exact structure:
## Game Title
[Creative, descriptive name]
Core Concept(s) Being Reinforced

Concept 1: [Brief description]
Concept 2: [Brief description if applicable]
Concept 3: [Brief description if applicable]

## Game Mechanics
Objective: What is the player trying to achieve?
How to Play: Step-by-step gameplay flow (3-5 steps)
Interaction Type: [Click, drag-and-drop, typing, multiple choice, etc.]
Scoring/Progress: How does the player know they're succeeding?
Learning Style Integration
Explain how the game specifically caters to the user's learning profile:

[How it matches their preferred learning style]
[How it aligns with their engagement preferences]

Technical Implementation Notes
Brief notes for the React developer who will implement this as a SINGLE, SELF-CONTAINED component:

Main UI Sections: [List 2-3 key sections within the component]
State Management: [What React state variables are needed using useState]
Data Structures: [What information needs to be stored/tracked in component state]
User Interface Elements: [Key UI components needed - buttons, inputs, displays, etc.]
Event Handlers: [What user interactions need to be handled]
Styling Approach: [Suggest Tailwind CSS classes for key visual elements]
Component Structure: [Brief outline of JSX structure]

CRITICAL IMPLEMENTATION REQUIREMENTS:

Must be a single React functional component with default export
All game logic contained within this one component
Use only React useState/useEffect hooks (no external state management)
No external dependencies beyond React and Tailwind CSS
Must be embeddable directly into an education website
Component should be fully self-contained and portable

Success Metrics
How will you know the game is working educationally?

[2-3 specific learning outcomes the game should achieve]

## Important Guidelines

Focus on ONE clear game concept rather than multiple options
Ensure the game directly teaches the content rather than just testing recall
Make the connection between gameplay and learning explicit
SINGLE COMPONENT REQUIREMENT: The game must be implementable as ONE self-contained React component
Design for embedding in education websites without external dependencies
Keep the scope realistic for a single React functional component
All game state and logic must fit within React component state (useState hooks)
Consider accessibility and different skill levels

Design a game that makes learning these concepts engaging, memorable, and effective for this specific user.
"""

GAME_GEN_SYSTEM_PROMPT = """ You are creating React game components that render educational content. Technical requirements:
- Use React.createElement (no JSX)
- Use React hooks without React. prefix (useState, useEffect, etc.)
- Return single root element with white background
- Container uses width: 100%, height: 100% with 5:6 aspect ratio
- Use relative units (%, vh, vw) for responsive design
- Include error handling with try-catch blocks
- Use requestAnimationFrame for smooth animations
- use Tailwind classes for styling
"""


GAME_CODE_PROMPT = """
Task Overview
Generate a fully functional React component based on the provided game concept. The component will be dynamically executed within a DynamicGameComponent wrapper.
Game Concept to Implement
{game_idea}
Technical Execution Context
Your generated code will be executed in this pattern:
javascriptconst ComponentFunction = new Function('React', 'useState', 'useEffect', 'useRef', 'useCallback', 'MathJax', `
  // YOUR CODE GOES HERE
  return React.createElement('div', /* your component implementation */);
`);
Code Structure Requirements
1. React Hooks Usage

Use hooks WITHOUT React prefix: useState, useEffect, useRef, useCallback
All hooks must be called at the top level of the component
Do not use custom hooks or external state management

2. Element Creation - CRITICAL REQUIREMENT

Use ONLY React.createElement(tagName, props, children)
ABSOLUTELY NO JSX syntax allowed - this will cause runtime errors
For CSS classes, use the className property in the props object
Structure: React.createElement('div', /{className: 'game-container'/}, [child1, child2])
WRONG: <div className="test"> or any JSX
CORRECT: React.createElement('div', {className: 'test'})

3. Component Structure
javascript// Hook declarations
const [gameState, setGameState] = useState(initialValue);
const [score, setScore] = useState(0);
// ... other hooks

// Event handlers and game logic functions
const handleClick = useCallback((event) => {
  // event handling logic
}, [dependencies]);

// Game logic functions
const updateGame = () => {
  // game update logic
};

// Main render return
return React.createElement('div', {
  className: 'game-container',
  style: { width: '100%', height: '100%', backgroundColor: 'white' }
}, [
  // Array of child elements
  React.createElement('h2', {key: 'title'}, 'Game Title'),
  React.createElement('div', {key: 'instructions'}, 'How to play...'),
  // ... other elements
]);
Responsive Design Requirements
Container Specifications

Parent container: Portrait orientation, aspect ratio 5:6, right half of screen
Your component receives: width: 100%, height: 100%
Background: Always white (backgroundColor: 'white')

Scaling Implementation
javascriptconst containerRef = useRef(null);
const [scale, setScale] = useState(1);

useEffect(() => {
  const updateScale = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      // Calculate appropriate scale based on container size
      const newScale = Math.min(rect.width / baseWidth, rect.height / baseHeight);
      setScale(newScale);
    }
  };
  
  updateScale();
  window.addEventListener('resize', updateScale);
  return () => window.removeEventListener('resize', updateScale);
}, []);
User Interface Requirements
1. Game Instructions
Include clear, visible instructions that explain:

How to play the game
Connection to educational content
Controls and objectives

2. Interactive Elements

Start/Restart button
Score display
Progress indicators
Clear feedback for user actions

3. Keyboard Input (if needed)
javascriptuseEffect(() => {
  const handleKeyPress = (e) => {
    if (gameActive && containerRef.current === document.activeElement) {
      e.preventDefault();
      // Handle key input
    }
  };
  
  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, [gameActive]);
Error Prevention Guidelines
1. Safe Data Access
javascript// Use optional chaining
const value = data?.property?.subProperty;

// Check array bounds
if (array && index >= 0 && index < array.length) {
  // Safe to access array[index]
}
2. Mathematical Operations
javascript// NO eval() - use explicit calculations
const result = Math.sin(angle) + Math.cos(angle);

// Wrap calculations in try-catch
try {
  const calculation = performComplexMath(input);
  setResult(calculation);
} catch (error) {
  setError('Invalid calculation');
}
3. Animation and Game Loops
javascriptuseEffect(() => {
  let animationId;
  
  const gameLoop = () => {
    updateGame();
    animationId = requestAnimationFrame(gameLoop);
  };
  
  if (gameActive) {
    animationId = requestAnimationFrame(gameLoop);
  }
  
  return () => {
    if (animationId) {
      cancelAnimationFrame(animationId);
    }
  };
}, [gameActive]);
Code Quality Requirements

Variable Names: Never use reserved keywords (function → gameFunction)
Error Boundaries: Wrap risky operations in try-catch blocks
Memory Management: Clean up event listeners and animations
Performance: Use useCallback for event handlers, useMemo for expensive calculations
Accessibility: Include tabIndex={0} for keyboard-interactive elements

Output Format - CRITICAL
Provide ONLY the JavaScript code that goes inside the component function. Your code will be executed in this exact context:
javascriptconst ComponentFunction = new Function('React', 'useState', 'useEffect', 'useRef', 'useCallback', 'MathJax', `
  // YOUR CODE GOES HERE - NO JSX ALLOWED
  return React.createElement(/* your elements */);
`);
ABSOLUTE REQUIREMENTS:

NO JSX syntax anywhere (<div>, <button>, etc.) - this will cause errors
NO import statements
NO function wrappers
NO explanatory text or comments
NO markdown formatting
Use only React.createElement for ALL elements
Start directly with your hook declarations and logic

Example Structure Template - FOLLOW THIS EXACTLY
javascriptconst [gameData, setGameData] = useState(0);
const [score, setScore] = useState(0);
const containerRef = useRef(null);

const handleClick = useCallback(() => {
  setScore(score + 1);
}, [score]);

const handleStart = useCallback(() => {
  setGameData(1);
}, []);

useEffect(() => {
  // Any setup code here
}, []);

return React.createElement('div', {
  ref: containerRef,
  tabIndex: 0,
  style: { 
    width: '100%', 
    height: '100%', 
    backgroundColor: 'white',
    padding: '20px',
    outline: 'none'
  }
}, [
  React.createElement('h2', {
    key: 'title',
    style: { marginBottom: '10px' }
  }, 'Fraction Game'),
  React.createElement('div', {
    key: 'instructions',
    style: { marginBottom: '20px' }
  }, 'Click the correct equivalent fraction!'),
  React.createElement('button', {
    key: 'start',
    onClick: handleStart,
    style: { padding: '10px 20px', fontSize: '16px' }
  }, 'Start Game'),
  React.createElement('div', {
    key: 'score',
    style: { marginTop: '10px' }
  }, `Score: ${score}`)
]);
Remember:

Every element must use React.createElement
Props go in the second parameter as an object
Children go in the third parameter (single child or array of children)
Use key prop for array children
Use style object for inline styles or className for CSS classes

Generate the complete game code now:
"""


GAME_CODE_PROMPT_OLD = """
Create a fully functional React component for the following game idea that integrates concepts from multiple learning materials:

    ## GAME IDEA:
    {game_idea}

    The component will be rendered within a DynamicGameComponent. Your task is to generate the code that will be passed to this component.

            ```javascript
            const DynamicGameComponent = (((this is where the game code will be passed in as an argument))) => {{
              const [error, setError] = useState(null);
              const [GameComponent, setGameComponent] = useState(null);

              useEffect(() => {{
                setError(null);
                if (gameCode.startsWith("Error generating game code:")) {{
                  setError(gameCode);
                  return;
                }}
                try {{
                  // Your generated code will be inserted here
                  const ComponentFunction = new Function('React', 'useState', 'useEffect', 'MathJax', `
                    return function Game() {{
                      // Your generated code goes here
                    }}
                  `);

                  const CreatedComponent = () => {{
                    return (
                      <ErrorBoundary>
                        {{ComponentFunction(React, React.useState, React.useEffect, MathJax)}}
                      </ErrorBoundary>
                    );
                  }};
                  setGameComponent(() => CreatedComponent);
                }} catch (err) {{
                  console.error('Error creating game component:', err);
                  setError('Error: (((this is where error output would go))));
                }}
              }}, [gameCode]);

              // ... rest of the component
            }};
            ```

            Requirements:
                1. Use React hooks (useState, useEffect, useRef, useCallback) without React. prefix
                2. Use React.createElement for all element creation (no JSX)
                3. Return a single root element (usually a div) containing all other elements 
                4. Ensure all variables and functions are properly declared
                5. Do not use any external libraries or components not provided
                6. Provide ONLY the JavaScript code, without any explanations or markdown formatting
                7. Do not include 'return function Game() {{' at the beginning or '}}' at the end
                8. Use proper JavaScript syntax (no semicolons after blocks or object literals in arrays)
                9. Do not use 'function' as a variable name, as it is a reserved keyword in JavaScript. Use 'func' or 'mathFunction' instead
                10. Create instructions for the user on how to play the game in the game component and how it relates to the chapter content
                11. When evaluating mathematical expressions or functions, use a safe evaluation method instead of 'eval'. For example:
                    - For simple arithmetic, use basic JavaScript operations
                    - For more complex functions, define them explicitly (e.g., Math.sin, Math.cos, etc.)
                12. Ensure all variables used in calculations are properly defined and initialized
                13. Use try-catch blocks when performing calculations to handle potential errors gracefully
                14. For keyboard input:
                    - Use the useEffect hook to add and remove event listeners for keyboard events
                    - In the event listener, call e.preventDefault() to prevent default browser behavior (like scrolling)
                    - Focus on a game element (like the canvas) when the component mounts to ensure it captures keyboard events
                15. Add a button to start/restart the game, and only capture keyboard input when the game is active
                16. Ensure that the current equation is always visible and properly rendered using plain text or another method
                17. To prevent scrolling when using arrow keys:
                    - Add 'tabIndex={{0}}' to the game container div to make it focusable
                    - In the useEffect for keyboard events, check if the game container has focus before handling key presses
                18. Display the current function prominently using plain text, and update it whenever it changes
                19. Use requestAnimationFrame for the game loop to ensure smooth animation
                20. Add error checking before accessing array elements or object properties
                21. Use optional chaining (?.) when accessing nested properties to prevent errors
                22. The background color of the dynamic game component is white keep this as the background color of the game.
                23. Do not forget to include instructions for the user on how to play the game in the game component and how it relates to the chapter content as text in the game component.
                24. Container Sizing Requirements:
                    - The container is the parent of the game component and is in a portrait orientation occupying vertically the right half of the screen(it's aspect ratio is 5:6)
                    - The game must automatically scale to fit its container width without scrollbars
                    - Use relative units (%, vh, vw) instead of fixed pixel values
                    - All game elements must be sized relative to their container
                    - The game container uses width: 100% and height: 100%
                    - Add a useEffect hook to handle window resizing and maintain proper scaling
                    - Ensure the game's aspect ratio is maintained while fitting the width
                    - Use transform: scale() if needed to ensure proper fitting
                    - Set initial dimensions using percentages of the parent container
                    - Listen for container size changes and update game element sizes accordingly
                    - Use getBoundingClientRect() to get accurate container dimensions
                    - Apply CSS transform-origin: top left when scaling
                
                25. Educational Features:
                    - Include an "Auto-Solve" or "Show Me How" button that demonstrates the correct procedure execution or step-by-step solution
                    - The auto-solve should animate step-by-step at a reasonable pace (500-1000ms per step)
                    - Highlight the elements/concepts being processed during auto-solve with visual indicators
                    - Allow users to pause/resume or stop the demonstration
                    - Consider adding speed controls (slow/medium/fast) for the demonstration
                    - Show progress indicators (current step, concepts covered, completion percentage, etc.)

                26. Learning Enhancement:
                    - Add tooltips or brief explanations during auto-solve about what's happening at each step
                    - Include a "Reset to Original" button to restart with the same content for comparison
                    - Consider showing complexity or difficulty information related to the topic
                    - Add a "Hint" system that suggests the next optimal step without fully solving
                    - Include visual feedback for correct vs suboptimal approaches

                27. Content Visualization:
                    - Use different colors/animations for different states (processing, completed, highlighted concepts)
                    - Show the completed portion vs remaining content clearly
                    - Include a progress bar showing how close to completion the demonstration is
                    - Use visual hierarchies to distinguish between different concept levels or importance

                  28. User Experience:
                    - Provide clear feedback for invalid actions or incorrect attempts
                    - Add confirmation for reset actions
                    - Include keyboard shortcuts for common actions
                    - Add accessibility features (ARIA labels, keyboard navigation, screen reader support)
                    - Consider mobile-responsive touch interactions
                    - Ensure content scales appropriately across different screen sizes
                                                                
            Generate the game code now, remember to not include any explanations or comments, just the code:
"""


TOOLS_AVAILABLE = {
    "diagram": {
        "name": "diagram",
        "description": "Generates visual diagrams using mermaid syntax"
    },
    "game": {
        "name": "game",
        "description": "Creates interactive learning games and challenges using javascript and React"
    },
    "flashcard": {
        "name": "flashcard",
        "description": "Generates flashcards for student review"
    },
    "quiz": {
        "name": "quiz",
        "description": "Generates quiz questions for student assessment, practice, learning or understanding"
    },
    "visualization": {
        "name": "visualization",
        "description": "Creates AI-generated image sequences to visualize complex concepts and processes as an educational slideshow (EXPENSIVE - use sparingly only for complex visual concepts that benefit from step-by-step imagery)"
    },
}


def build_chat_message_prompt(
    learning_profile: str,
    title: str,
    page_content: str,
    user_message: str,
    chapter_name: str = None,
    section_name: str = None,
) -> list[dict]:

    context_sections = []

    context_sections.append(f"## Learning Context\nUser Profile: {learning_profile}")

    if title:
        context_sections.append(f"## Book: {title}")
    if chapter_name:
        context_sections.append(f"## Chapter: {chapter_name}")
    if section_name:
        context_sections.append(f"## Section: {section_name}")

    context_sections.append(f"## Currently Page Content of the book\n```\n{page_content}\n```")
    context_sections.append(f"## User Question\n{user_message}")

    tool_instruction = f"""
        ## Response Guidelines

        You are an adaptive educational assistant (Adaptively) helping a learner understand the material above. 

        **Primary Goal**: Provide clear, educational explanations that match the user's learning profile and directly address their question about the current content.

        **Response Style**:
        - Respond with confidence and authority about the material
        - NEVER say "according to the text provided" or "based on the content given" 
        - Act as if you naturally know this book and its content
        - Reference specific concepts, chapters, or sections naturally (e.g., "In this chapter on photosynthesis..." not "According to the text about photosynthesis...")
        - Make the user feel you're their knowledgeable tutor, not just reading from their materials

        ---
        
        ## Available Tools (STRICT)
        {TOOLS_AVAILABLE}
        
        ---
        
        ### Tool Usage Instructions (STRICT)

        **Only use tools when they would clearly enhance learning for THIS specific question.**

        - Do NOT reply with information when a tool can don that better, like diagrams, flashcard, etc.
        - DO NOT use tools just to make your answer seem fancy.
        - DO NOT use tools for things you can explain yourself (definitions, concepts, summaries).
        - **DO NOT generate diagrams, games, etc. manually — ask the backend tool. (STRICT)**
        - DO NOT include `"args"` or extra data — backend will handle it.

        #### When to Use a Tool:
        - The user asks for a diagram, file formatter, or visual/interactive element.
        - A tool is the **only clear way** to help them understand something better.

        #### When NOT to Use a Tool:
        - For generic explanations
        - Just to show off features
        - If the question can be answered well with plain language

        ---
        
        ## Tool Name Format (STRICT)
         **Use the exact tool name as provided in the TOOLS_AVAILABLE dictionary.**

        ### TOOL CALL Format (STRICT)

        **Only use this exact format, with no additional text or explanation:**

        ```text
        TOOL_CALL: {{"tool": "tool_name"}}
        
        NO MISTAKES
      """


    # Final system message
    full_system_prompt = "\n\n".join(context_sections + [tool_instruction])

    return [
        {"role": "system", "content": full_system_prompt},
        {"role": "user", "content": user_message},
    ]
    
    
    
FLASHCARD_SYSTEM_PROMPT = """
You are an expert tutor specializing in creating effective flashcards for student revision.
Your task is to generate flashcards that are:
- Clear and focused on one concept per card
- Appropriate for the student's learning level
- Formatted as valid JSON only

CRITICAL: You must respond with ONLY valid JSON. No explanations, no markdown formatting, no additional text.
"""

FLASH_CARD_GENERATION_PROMPT = """
# Flashcard Generation Task

## Document Information
- **Title**: {title}
- **Chapter**: {chapter_name}
- **Section**: {section_name}
- **Learning Profile**: {learning_profile}
- **Target Count**: {count}

## Content to Process
```
{content}
```

## Output Format (STRICT)
Generate exactly **{count}** flashcards as a JSON array. Each flashcard must be an object with these exact keys:

```json
[
  {{
    "id": "f1",
    "question": "Clear question text here",
    "answer": "Concise but complete answer here",
    "difficulty": 3,
    "topic": "Main topic or concept",
  }},
  {{
    "id": "f2",
    "question": "Another question...",
    "answer": "Another answer...",
    "difficulty": 2,
    "topic": "Another topic or concept",
  }}
]
```

## Requirements
  - Questions should be clear and test **understanding**, not just memorization  
  - Answers should be **concise but complete**  
  - Adapt difficulty and style to the **learning profile**  
  - Focus on the **most important concepts** from the content  
  - Ensure variety in question types (definition, application, comparison, etc.)  

## Critical Instructions (STRICT)
**Return ONLY the JSON array, no other text or formatting**
"""


QUIZ_GENERATION_SYSTEM_PROMPT = """
You are an expert educational content creator specializing in generating quiz questions for student assessment.
Your task is to create high-quality quiz questions that:
- Test understanding, not just memorization
- Follow proper structure with options, correct answer, explanation, and metadata
- Match the learning level based on the student profile
- Are returned as STRICT JSON only — no extra text, markdown, or formatting

CRITICAL: Return ONLY valid JSON following the required schema. No explanations, no code formatting, no commentary.
"""


QUIZ_GENERATION_USER_PROMPT = """
# Quiz Question Generation Task

## Document Information
- **Title**: {title}
- **Chapter**: {chapter_name}
- **Section**: {section_name}
- **Learning Profile**: {learning_profile}
- **Target Count**: {count}

## Content to Process
{content}

## Output Format (STRICT)
Generate exactly **{count}** quiz questions as a JSON array. Each object must follow this schema:

## Multiple Choice Example (STRICT)
[
  {{
    "id": "q1",
    "question": "What is the main advantage of using a hash table?",
    "options": ["a) Constant time access", "b) Sorted data", "c) Low memory usage", "d) Simplified recursion"],
    "correct_answer": "a) Constant time access",
    "explanation": "Hash tables offer average-case constant time complexity for insertions and lookups, which is ideal for fast access.",
    "difficulty": 2,
    "topic": "Data Structures",
    "question_type": "multiple_choice"
  }}
]

## True/False Example (STRICT)
[
  {{
    "id": "q2",
    "question": "In a max-heap, the smallest element is always at the root.",
    "options": ["a) True", "b) False"],
    "correct_answer": "b) False",
    "explanation": "In a max-heap, the root node contains the maximum element, not the smallest.",
    "difficulty": 1,
    "topic": "Data Structures",
    "question_type": "true_false"
  }}
]

## Short Answer Example (STRICT)
[
  {{
    "id": "q3",
    "question": "What does the acronym 'API' stand for?",
    "options": [],
    "correct_answer": "Application Programming Interface",
    "explanation": "API stands for Application Programming Interface, which allows communication between software components.",
    "difficulty": 1,
    "topic": "Software Engineering",
    "question_type": "short_answer"
  }}
]
"""

EXPANSION_SYSTEM_PROMPT = """
You are a query rewriting expert that enhances user queries for retrieval-augmented generation (RAG) tasks.

Your responsibilities:
1. Transform short or ambiguous queries into clear, standalone questions.
2. Add contextual relevance to improve search accuracy across technical or academic documents.
3. Maintain the original intent of the user’s query — do not introduce unrelated assumptions.
4. Return a refined version of the query that is specific, self-contained, and optimized for retrieval.

Guidelines:
- Use formal and precise language.
- Do not include any explanations or prefixes like 'Expanded:' or 'Rewritten:'.
- Return only the improved query as plain text.
- Do not ask clarifying questions or reference external sources.

This query will be embedded and used to retrieve relevant documents. Ensure it is complete and unambiguous.
"""

MCQ_GEN_SYSTEM_PROMPT = """
You are an expert educational content creator specializing in generating quiz questions for student assessment.
Your task is to create high-quality quiz questions that:
- Test understanding, not just memorization
- Follow proper structure with options, correct answer{EXPLANATION_INSTRUCTION}, and metadata
- Match the {DIFFICULTY_LEVEL} difficulty level
- Are returned as STRICT JSON only — no extra text, markdown, or formatting

CRITICAL: Return ONLY valid JSON following the required schema. No explanations, no code formatting, no commentary.

{DIFFICULTY_SPECIFIC_INSTRUCTIONS}
"""

MCQ_GEN_USER_PROMPT = """
# Quiz Question Generation Task

## Generation Parameters
- **Difficulty Level**: {DIFFICULTY_LEVEL}
- **Target Count**: {K}

## Content to Process
{CONTENT}

## Output Format (STRICT)
Generate exactly **{K}** quiz questions as a JSON array. Each object must follow this schema:

## Multiple Choice Example (STRICT)
[
 {{
   "id": "q1",
   "question": "What is the main advantage of using a hash table?",
   "options": ["a) Constant time access", "b) Sorted data", "c) Low memory usage", "d) Simplified recursion"],
   "correct_answer": "a) Constant time access",{EXPLANATION_FIELD}
 }}
]

Return ONLY the JSON array with {K} questions. No additional text or formatting.
"""

EASY_DIFFICULTY_INSTRUCTIONS = """EASY DIFFICULTY GUIDELINES (difficulty: 1):
- Focus on basic concepts, definitions, and fundamental principles
- Use straightforward language and familiar terminology  
- Questions should test recall and basic understanding
- Avoid complex scenarios or multi-step reasoning
- Include direct fact-based questions
- Make incorrect options clearly distinguishable from the correct answer{EXPLANATION_DIFFICULTY_NOTE}
- Difficulty number in JSON should be 1"""

MEDIUM_DIFFICULTY_INSTRUCTIONS = """MEDIUM DIFFICULTY GUIDELINES (difficulty: 2):
- Focus on application of concepts and analytical thinking
- Include scenario-based questions that require understanding relationships
- Test comprehension and ability to apply knowledge to new situations
- Use moderate complexity in language and concepts
- Include some questions requiring comparison or classification
- Make distractors more plausible but still clearly incorrect{EXPLANATION_DIFFICULTY_NOTE}
- Difficulty number in JSON should be 2"""

HARD_DIFFICULTY_INSTRUCTIONS = """HARD DIFFICULTY GUIDELINES (difficulty: 3):
- Focus on synthesis, evaluation, and complex problem-solving
- Include multi-layered questions requiring deep understanding
- Test critical thinking and ability to analyze complex scenarios
- Use advanced terminology and sophisticated concepts
- Include questions requiring students to evaluate, predict, or justify
- Make distractors very plausible, requiring careful consideration
- Include questions that test edge cases or exceptions to rules{EXPLANATION_DIFFICULTY_NOTE}
- Difficulty number in JSON should be 3"""

MIXED_DIFFICULTY_INSTRUCTIONS = """MIXED DIFFICULTY GUIDELINES:
- Create a balanced distribution: 30% easy (difficulty: 1), 40% medium (difficulty: 2), 30% hard (difficulty: 3)
- Vary the difficulty number in JSON based on question complexity
- Easy questions: Test basic recall and definitions
- Medium questions: Test application and analysis  
- Hard questions: Test synthesis and evaluation
- Ensure variety in question types and cognitive levels{EXPLANATION_DIFFICULTY_NOTE}"""

# Difficulty level to number mapping
DIFFICULTY_MAPPING = {
   "easy": 1,
   "medium": 2,
   "hard": 3,
   "mixed": "varies"
}

# Difficulty level to instructions mapping
INSTRUCTION_MAPPING = {
   "easy": EASY_DIFFICULTY_INSTRUCTIONS,
   "medium": MEDIUM_DIFFICULTY_INSTRUCTIONS,
   "hard": HARD_DIFFICULTY_INSTRUCTIONS,
   "mixed": MIXED_DIFFICULTY_INSTRUCTIONS
}

# Explanation toggle configurations
EXPLANATION_CONFIGS = {
   "with_explanations": {
       "EXPLANATION_INSTRUCTION": ", explanation",
       "EXPLANATION_FIELD": '\n    "explanation": "{EXPLANATION_TEXT}",',
       "EXPLANATION_DIFFICULTY_NOTE": "\n- Provide clear, educational explanations for correct answers"
   },
   "without_explanations": {
       "EXPLANATION_INSTRUCTION": "",
       "EXPLANATION_FIELD": "",
       "EXPLANATION_DIFFICULTY_NOTE": ""
   }
}



RAG_SYSTEM_PROMPT = """
You are The Librarian, an expert AI assistant that helps users understand information from their personal document library. 
You excel at connecting concepts across different documents and providing insightful and very **CONCISE** answers based on retrieved content.

CORE PRINCIPLES:
- Synthesize information intelligently from multiple sources
- Connect related concepts even if they appear in different documents **CONSISELY**
- Provide specific, actionable answers based on the available content
- Be confident in drawing reasonable conclusions from the excerpts
- Focus on what the documents DO contain rather than what they don't
"""


ASK_MY_LIBRARY_USER_PROMPT = """
Based on the excerpts from your document library, I'll answer your question about: {query}

RELEVANT CONTENT FROM YOUR DOCUMENTS:
{context}

INSTRUCTIONS:
1. Analyze the provided excerpts carefully for relevant information
2. Connect concepts across different documents when applicable, don't force it
3. Provide a CONSISE clear, informative answer based on what's available
4. If multiple topics are mentioned in the query, address each one using the relevant excerpts
5. Be specific and cite which documents contain the information
6. Focus on synthesizing and explaining the content rather than stating limitations

Answer the user's question using the information provided above:
"""