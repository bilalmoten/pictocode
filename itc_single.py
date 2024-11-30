import os
from pathlib import Path
import base64
import requests
import logging
from typing import Optional
from dotenv import load_dotenv
import time
import threading

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
# INITIAL_CODES_PATH = BASE_PATH / "initial"

# Create codes directory if it doesn't exist
CODES_PATH.mkdir(exist_ok=True)
# INITIAL_CODES_PATH.mkdir(exist_ok=True)


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
               - Layout
               - Image placement and creative uses like randomized grids etc if any
               - Background treatments and overlays if any
               - Typography hierarchy
               - Interactive elements
               - Spacing and alignment patterns
            
            Development Approach:
            1. First understand the component's purpose and design intent
            2. Identify creative patterns and visual effects
            3. Plan the responsive behavior
            4. Consider all possible component states
            5. Choose appropriate technical solutions
            6. Write the HTML/Tailwind CSS code, along with a detailed descriptive analysis of the design provided to you. Describe the design in detail, including the layout, image placement, background treatments, typography, interactive elements, and spacing.
            7. For the code, do not start with <!DOCTYPE html>, <html>, <head>, <body> tags, just start with the <div> tag.
            
            Remember:
            - Use semantic HTML tags appropriately
            - For Icons, use FontAwesome icons, not SVGs or other libraries.
            - For Images, use placeholder image url (https://placehold.co/600x400/EEE/31343C)
            - For Videos, use place holder video adderss (https://videos.pexels.com/video-files/6768212/6768212-uhd_1440_2732_30fps.mp4)
            - Implement responsive design using Tailwind breakpoints
             """,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Here is the {section_type} Section design. """,
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
        "temperature": 0.4,
        "top_p": 0.95,
        "max_tokens": 4000,
    }

    try:
        response = requests.post(GPT4O_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        # Save the enhanced code
        # output_file = INITIAL_CODES_PATH / section_type / f"{image_path.stem}.html"
        # with open(output_file, "w", encoding="utf-8") as f:
        #     f.write(result["choices"][0]["message"]["content"])

        # logger.info(f"Successfully processed initial code for {image_path.name}")
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
    You are an expert web developer specializing in modern responsive web development using HTML and Tailwind CSS.
    Your task is to enhance the given {section_type} section code. As per your understanding and experience, add subtle animations using Tailwind CSS, improve accessibility and make it more professional while maintaining the layout and design intent. 
    
    REMEMBER: Your job is to understand the design intent and enhance the code accordingly. 
    
    You are expected to output only the enhanced code, without any explanations. No backticks.
    
    Technical Requirements:
    - Use semantic HTML tags appropriately
    - Implement responsive design using Tailwind breakpoints
    - For Icons, use FontAwesome icons, not SVGs or other libraries.
    - For Images, use this placeholder image url (https://placehold.co/600x400/EEE/31343C)
    - For Videos, use this place holder video url (https://videos.pexels.com/video-files/6768212/6768212-uhd_1440_2732_30fps.mp4)
    - Add subtle transitions and hover effects where appropriate
    - Return HTML code only, styling should be done with Tailwind CSS. Using javascript if needed for essential functionality, like for dropdowns, accordions, etc.
    - Make sure the final code is wrapped in needed HTML tags, like <div>, <section>, <article>, etc.
    - Return only the enhanced code without any explanations. No backticks.

    
    Here's the code to enhance:
    
    {initial_code}
    
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


# def print_elapsed_time(start_time, image_name):
#     while getattr(threading.current_thread(), "do_run", True):
#         elapsed_time = time.time() - start_time
#         print(
#             f"\rProcessing {image_name}: {elapsed_time:.2f} seconds", end="", flush=True
#         )
#         time.sleep(0.1)


# Process all images from each section
for section_folder in SECTIONS_PATH.iterdir():
    if section_folder.is_dir():
        section_type = section_folder.name
        logger.info(f"Processing {section_type} section...")

        # Create output directory for this section
        output_section_path = CODES_PATH / section_type
        output_section_path.mkdir(exist_ok=True)

        # Get all images from the section folder
        image_files = list(section_folder.glob("*"))
        if not image_files:
            logger.warning(f"No images found in {section_type} folder")
            continue

        # Process all images
        for image_path in image_files:
            try:
                start_time = time.time()
                logger.info(f"Processing image: {image_path.name}")

                # # Start the timer thread
                # timer_thread = threading.Thread(
                #     target=print_elapsed_time, args=(start_time, image_path.name)
                # )
                # timer_thread.daemon = True
                # timer_thread.start()

                # Encode image
                base64_image = encode_image(str(image_path))

                # Get initial HTML from GPT-4V
                initial_code = call_gpt4o(base64_image, section_type)

                # Enhance code with O1-mini
                enhanced_code = enhance_with_o1_mini(initial_code, section_type)

                # Save the enhanced code
                output_file = output_section_path / f"{image_path.stem}.html"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(enhanced_code)
                # # Stop the timer thread
                # timer_thread.do_run = False
                # timer_thread.join()
                end_time = time.time()
                processing_time = end_time - start_time
                logger.info(
                    f"Successfully processed {image_path.name} in {processing_time:.2f} seconds"
                )

            except Exception as e:
                logger.error(f"Error processing {image_path.name}: {str(e)}")
                continue  # Continue with next image even if one fails
