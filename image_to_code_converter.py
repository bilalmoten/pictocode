import os
from pathlib import Path
import base64
import requests
import logging
from typing import Optional
from dotenv import load_dotenv
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Get environment variables
AZURE_KEY = os.getenv("AZURE_KEY")
GPT4O_ENDPOINT = os.getenv("GPT4o_ENDPOINT")
O1_MINI_ENDPOINT = os.getenv("O1_MINI_ENDPOINT")

# Define paths
BASE_PATH = Path.cwd()
SECTIONS_PATH = BASE_PATH / "sections"
CODES_PATH = BASE_PATH / "codes"

# Create codes directory if it doesn't exist
CODES_PATH.mkdir(exist_ok=True)

# # After defining paths, add these debug prints
# print(f"Current working directory: {BASE_PATH}")
# print(f"Sections path: {SECTIONS_PATH}")
# print(f"Looking for images in: {SECTIONS_PATH.absolute()}")

# if SECTIONS_PATH.exists():
#     print(f"✓ Sections directory exists at {SECTIONS_PATH}")
#     for item in SECTIONS_PATH.iterdir():
#         if item.is_dir():
#             print(f"\nChecking {item.name} directory:")
#             print(f"Path: {item.absolute()}")
#             # List all files in this section directory
#             files = list(item.glob("*"))
#             print(f"Files found: {len(files)}")
#             for file in files:
#                 print(f"  - {file.name} ({file.suffix})")
# else:
#     print("✗ Sections directory does not exist!")


def encode_image(image_path: str) -> str:
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def call_gpt4o(base64_image: str, section_type: str) -> Optional[str]:
    """Call GPT-4V (gpt4o) to generate initial HTML code"""
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_KEY,
    }

    messages = [
        {
            "role": "system",
            "content": """You are an expert web developer specializing in modern responsive web development.
            Your task is to analyze website component designs and convert them into production-ready code.

            Image Analysis Instructions:
            1. Each image contains desktop (left) and mobile (right) layouts
            2. Analyze the visual patterns and design elements:
               - Layout structure and grid systems
               - Image placement and creative uses
               - Background treatments and overlays
               - Typography hierarchy
               - Interactive elements
               - Spacing and alignment patterns
            
            Development Approach:
            1. First understand the component's purpose and design intent
            2. Identify creative patterns and visual effects
            3. Plan the responsive behavior
            4. Consider all possible component states
            5. Choose appropriate technical solutions
            
            Technical Requirements:
            - Use semantic HTML tags appropriately
            - Implement responsive design using Tailwind breakpoints
            - Add subtle transitions for interactive elements
            - Return HTML code only, styling should be done with Tailwind CSS
            - Make sure the final code is wrapped in needed HTML tags, like <div>, <section>, <article>, etc.
            - For Icons, use FontAwesome icons, not SVGs or other libraries.
            """,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Analyze this {section_type} design and convert it into a production-ready component.
                    Pay special attention to:
                    1. The creative use of images and layouts
                    2. Visual effects and overlays
                    3. Responsive behavior
                    4. Component states and interactions
                    
                    Return only the code.""",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        },
    ]

    payload = {
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 4000,
    }

    try:
        response = requests.post(GPT4O_ENDPOINT, headers=headers, json=payload)
        # Debug response
        # print(f"Response status code: {response.status_code}")
        # print(f"Response headers: {response.headers}")
        # print(f"Response body: {response.json()}")
        # print(f"Response text: {response.text}")

        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error in GPT-4V processing: {str(e)}")
        logger.error(f"Error in GPT-4V processing: {str(e)}")
        return None


def enhance_with_o1_mini(initial_code: str, section_type: str) -> Optional[str]:
    """Enhance the code using O1-mini model"""
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_KEY,
    }

    prompt = f"""
    Enhance this {section_type} section code. Add subtle animations using Tailwind CSS, improve accessibility, 
    and ensure it follows HTML and Tailwind CSS best practices. Make it more professional while maintaining 
    the original design intent.
    
    Think about how the code will be used in the final website. The code is written by a junior developer, so there might be mistakes, as his job is to convert figma to code, and he may have missed the proper implementation of things. So use your best judgement to improve the code.
    
    Here's the code to enhance:

    {initial_code}
    
    REMEMBER: 
    Technical Requirements:
    - Use semantic HTML tags appropriately
    - Implement responsive design using Tailwind breakpoints
    - Add subtle transitions for interactive elements
    - Return HTML code only, styling should be done with Tailwind CSS
    - Make sure the final code is wrapped in needed HTML tags, like <div>, <section>, <article>, etc.
    - Return only the enhanced code without any explanations. No backticks.
    - For Icons, use FontAwesome icons, not SVGs or other libraries.
    """

    messages = [{"role": "user", "content": prompt}]

    payload = {
        "messages": messages,
        "max_completion_tokens": 20000,
    }

    try:
        response = requests.post(O1_MINI_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error in O1-mini processing: {str(e)}")
        return None


# Process one image from each section
for section_folder in SECTIONS_PATH.iterdir():
    if section_folder.is_dir():
        section_type = section_folder.name
        logger.info(f"Processing {section_type} section...")

        # Create output directory for this section
        output_section_path = CODES_PATH / section_type
        output_section_path.mkdir(exist_ok=True)

        # Debug print for image pattern
        image_pattern = str(section_folder / "*.png")
        print(f"Looking for images with pattern: {image_pattern}")

        # Get first image from the section folder
        image_files = list(section_folder.glob("*"))
        # print(f"Found {len(image_files)} images in {section_type}")
        if not image_files:
            logger.warning(f"No images found in {section_type} folder")
            continue

        # Add this debug line after finding image files
        # if image_files:
        #     print(f"Found images: {[str(f.absolute()) for f in image_files]}")

        # Process only the first image
        image_path = image_files[0]
        try:
            logger.info(f"Processing image: {image_path.name}")

            # Encode image
            base64_image = encode_image(str(image_path))

            # Get initial HTML from GPT-4V
            initial_code = call_gpt4o(base64_image, section_type)
            if not initial_code:
                continue

            # Add delay to respect rate limits
            # time.sleep(2)

            # Enhance code with O1-mini
            enhanced_code = enhance_with_o1_mini(initial_code, section_type)
            if not enhanced_code:
                continue

            # Save the enhanced code
            output_file = CODES_PATH / section_type / f"{image_path.stem}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(enhanced_code)

            logger.info(f"Successfully processed {image_path.name}")

            # Add delay between sections
            time.sleep(2)

        except Exception as e:
            logger.error(f"Error processing {image_path.name}: {str(e)}")
