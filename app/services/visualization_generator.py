import asyncio
import logging
import base64
import httpx
import os
from typing import List, Dict, Any, Optional
from app.services.models import get_reply_from_model
from app.services.constants import DEFAULT_MODEL_ID  # Use UUID instead of model name
import json

logger = logging.getLogger(__name__)

# In-memory storage for testing (will move to DB later)
visualization_cache = {}

HUGGINGFACE_API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"


async def generate_visualization_script(
    content: str, 
    title: str, 
    chapter_name: str, 
    section_name: str, 
    learning_profile: Dict
) -> List[Dict]:
    """Generate a script with 3-5 descriptive scenes for visualization"""
    try:
        system_prompt = """You are an expert educational content visualizer. Your job is to create a series of 3-5 descriptive scenes that can be turned into images to help explain complex concepts.

IMPORTANT RULES:
1. Create exactly 3-5 scenes (no more due to API limits)
2. Each scene should be HIGHLY DESCRIPTIVE for image generation
3. Scenes should flow logically to tell a complete story
4. Use visual language that works well for AI image generation
5. Focus on scientific accuracy and educational value
6. Avoid text/words in scene descriptions (images can't generate readable text well)

Return ONLY a JSON array with this exact format:
[
  {"scene": 1, "description": "detailed visual description"},
  {"scene": 2, "description": "detailed visual description"},
  {"scene": 3, "description": "detailed visual description"}
]

Example for Object-Oriented Programming:
[
  {"scene": 1, "description": "Detailed cross-section view of a modern computer with glowing circuit boards, showing colorful data packets flowing through intricate pathways like a digital highway system, with bright blue and green LED lights illuminating the internal components, professional technical illustration style with clean lines and vibrant colors"},
  {"scene": 2, "description": "Abstract 3D visualization of class inheritance hierarchy with multiple interconnected geometric structures floating in space - a large golden parent class cube at the top connected by glowing silver lines to smaller child class pyramids and spheres below, each object casting subtle shadows and emanating soft colored light representing different methods and properties"},
  {"scene": 3, "description": "Dynamic scene showing object instantiation process with translucent blueprint-like wireframes transforming into solid, colorful 3D objects - a factory-like environment with conveyor belts carrying newly created instances, sparkling particles and energy effects surrounding the transformation process, futuristic industrial aesthetic with metallic surfaces and neon accents"}
]
"""

        user_prompt = f"""Create a visualization script for this educational content:

Title: {title}
Chapter: {chapter_name}
Section: {section_name}
Content: {content}


Generate 3-5 highly descriptive scenes that will help explain this concept visually."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        reply = get_reply_from_model(DEFAULT_MODEL_ID, messages)
        
        # Extract JSON from reply
        try:
            # Try to find JSON in the reply
            start = reply.find('[')
            end = reply.rfind(']') + 1
            if start != -1 and end > start:
                json_str = reply[start:end]
                script = json.loads(json_str)
                
                # Validate structure
                if isinstance(script, list) and len(script) <= 5:
                    for scene in script:
                        if not isinstance(scene, dict) or 'scene' not in scene or 'description' not in scene:
                            raise ValueError("Invalid scene structure")
                    
                    logger.info(f"Generated script with {len(script)} scenes")
                    return script
                else:
                    raise ValueError("Script validation failed")
                    
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse script JSON: {e}")
            # Fallback to a simple script
            return [
                {"scene": 1, "description": f"Educational illustration of {title}, scientific diagram style, clear and detailed"},
                {"scene": 2, "description": f"Process visualization for {chapter_name}, step-by-step illustration, professional academic style"},
                {"scene": 3, "description": f"Final concept summary for {section_name}, comprehensive diagram, textbook illustration style"}
            ]
            
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise


async def generate_single_image(description: str) -> Optional[str]:
    """Generate a single image using Hugging Face API and return base64"""
    try:
        from app.services.models import get_next_api_key
        
        api_key = get_next_api_key("huggingface")
        logger.info(f"Using Hugging Face API key from cycle rotation")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Enhance the prompt for better educational images
        enhanced_prompt = f"{description}, high quality, educational illustration, clean background, professional style, detailed, 4k"

        payload = {
            "inputs": enhanced_prompt,
            "parameters": {
                "num_inference_steps": 20,  # Lower for faster generation
                "guidance_scale": 7.5,
                "width": 512,
                "height": 512
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                HUGGINGFACE_API_URL,
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                # Convert image bytes to base64
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                logger.info(f"Successfully generated image for: {description[:50]}...")
                return image_base64
            else:
                logger.error(f"Image generation failed: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return None


async def generate_all_images(script: List[Dict]) -> List[Dict]:
    """Generate images for all scenes in the script"""
    try:
        # Limit to 5 scenes max for free tier
        limited_script = script[:5]
        
        # Generate images concurrently (but be mindful of rate limits)
        tasks = []
        for scene in limited_script:
            task = generate_single_image(scene["description"])
            tasks.append(task)

        # Wait for all images to be generated
        images = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result with images
        result = []
        for i, scene in enumerate(limited_script):
            image_base64 = images[i] if i < len(images) and not isinstance(images[i], Exception) else None
            
            result.append({
                "scene": scene["scene"],
                "description": scene["description"],
                "image_base64": image_base64,
                "generated": image_base64 is not None
            })

        successful_images = sum(1 for item in result if item["generated"])
        logger.info(f"Generated {successful_images}/{len(result)} images successfully")
        
        return result

    except Exception as e:
        logger.error(f"Batch image generation failed: {e}")
        raise


async def generate_visualization(
    content: str,
    title: str, 
    chapter_name: str,
    section_name: str,
    learning_profile: Dict
) -> Dict[str, Any]:
    """Main function to generate complete visualization with script and images"""
    try:
        logger.info(f"Starting visualization generation for: {title}")
        
        # Step 1: Generate script
        script = await generate_visualization_script(
            content, title, chapter_name, section_name, learning_profile
        )
        
        # Step 2: Generate images for each scene
        scenes_with_images = await generate_all_images(script)
        
        # Step 3: Build final response
        visualization_data = {
            "title": title,
            "chapter": chapter_name,
            "section": section_name,
            "total_scenes": len(scenes_with_images),
            "successful_generations": sum(1 for scene in scenes_with_images if scene["generated"]),
            "scenes": scenes_with_images,
            "metadata": {
                "learning_style": learning_profile.get("learning_style", "visual"),
                "difficulty_level": learning_profile.get("difficulty_level", "intermediate"),
                "generated_at": "2025-07-26T03:20:00Z"  # Could use datetime.utcnow().isoformat()
            }
        }
        
        # Store in memory cache for testing
        cache_key = f"{title}_{chapter_name}_{section_name}".replace(" ", "_").lower()
        visualization_cache[cache_key] = visualization_data
        
        logger.info(f"Visualization completed: {visualization_data['successful_generations']}/{visualization_data['total_scenes']} images generated")
        
        return visualization_data
        
    except Exception as e:
        logger.error(f"Visualization generation failed: {e}")
        raise


def get_cached_visualization(title: str, chapter_name: str, section_name: str) -> Optional[Dict]:
    """Retrieve cached visualization (for testing)"""
    cache_key = f"{title}_{chapter_name}_{section_name}".replace(" ", "_").lower()
    return visualization_cache.get(cache_key)


def clear_visualization_cache():
    """Clear the visualization cache"""
    global visualization_cache
    visualization_cache.clear()
    logger.info("Visualization cache cleared")
