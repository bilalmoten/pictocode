import os
from pathlib import Path
import requests
import logging
from dotenv import load_dotenv
from typing import Optional
import concurrent.futures
from functools import partial
import time
import json
from threading import Lock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Get environment variables
AZURE_KEY = os.getenv("AZURE_KEY")
O1_MINI_ENDPOINT = os.getenv("O1_MINI_ENDPOINT")


def generate_component_description(code: str, section_type: str) -> Optional[str]:
    """
    Generate a concise description of a component's structure and design patterns.

    Args:
        section_type (str): The type of section (e.g., hero, features, pricing)
        code (str): The HTML/Tailwind CSS code of the component

    Returns:
        Optional[str]: A structured description of the component or None if failed
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_KEY,
    }

    prompt = f"""
    You are an expert in analyzing web components and creating clear, structured descriptions.
    Your task is to analyze this {section_type} component and create a concise description focusing on its structure and design patterns.
    
    Focus on describing:
    1. Layout pattern (e.g., "2-column grid with image left, content right")
    2. Visual hierarchy (e.g., "Prominent heading with supporting text below")
    3. Key interactive elements (e.g., "Hoverable cards with subtle animations")
    4. Responsive behavior (e.g., "Stacks vertically on mobile")
    5. Special features (e.g., "Includes image carousel", "Features testimonial cards")
    
    Guidelines:
    - Keep descriptions under 100 words
    - Focus on structure and design patterns, not content
    - Use clear, technical language
    - Highlight unique design features
    - Describe the component in a way that helps AI understand when to use it
    
    Here's the code to analyze:
    
    {code}
    
    Return only the description, no explanations or additional text.
    """

    messages = [{"role": "user", "content": prompt}]

    payload = {
        "messages": messages,
        "max_completion_tokens": 3000,
    }

    try:
        response = requests.post(O1_MINI_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Error generating description: {str(e)}")
        return None


def process_single_component(html_file: Path, section_type: str) -> tuple:
    """Process a single component and return its description"""
    try:
        start_time = time.time()
        logger.info(f"Processing component: {html_file.name}")

        with open(html_file, "r", encoding="utf-8") as f:
            code = f.read()

        description = generate_component_description(code, section_type)

        processing_time = time.time() - start_time
        logger.info(f"Processed {html_file.name} in {processing_time:.2f} seconds")

        return section_type, html_file.stem, description

    except Exception as e:
        logger.error(f"Error processing {html_file.name}: {str(e)}")
        return section_type, html_file.stem, None


def save_descriptions(descriptions: dict, output_file: str):
    """Save descriptions to file with error handling"""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(descriptions, f, indent=2)
        logger.info(f"Saved descriptions to {output_file}")
    except Exception as e:
        logger.error(f"Error saving descriptions: {str(e)}")


def process_components_directory(input_dir: str, output_file: str):
    """Process all HTML files in parallel and generate descriptions."""
    import json
    from threading import Lock

    base_path = Path(input_dir)
    max_workers = 20  # testing
    descriptions_lock = Lock()

    # Load existing descriptions
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            descriptions = json.load(f)
        logger.info(f"Loaded existing descriptions from {output_file}")
    else:
        descriptions = {}

    try:
        # Collect all tasks
        tasks = []
        for section_folder in base_path.iterdir():
            if not section_folder.is_dir():
                continue

            section_type = section_folder.name
            if section_type not in descriptions:
                descriptions[section_type] = {}

            for html_file in section_folder.glob("*.html"):
                # Skip if description already exists
                if html_file.stem in descriptions.get(section_type, {}):
                    continue
                tasks.append((html_file, section_type))

        logger.info(f"Found {len(tasks)} components to process")

        # Process components in parallel
        completed_descriptions = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_single_component, html_file, section_type): (
                    html_file,
                    section_type,
                )
                for html_file, section_type in tasks
            }

            for future in concurrent.futures.as_completed(futures):
                section_type, component_id, description = future.result()
                if description:
                    with descriptions_lock:
                        descriptions.setdefault(section_type, {})[
                            component_id
                        ] = description
                        completed_descriptions.append((section_type, component_id))

                        # Save periodically (e.g., every 5 components)
                        if len(completed_descriptions) % 20 == 0:
                            save_descriptions(descriptions, output_file)

        # Final save
        save_descriptions(descriptions, output_file)
        logger.info(f"Successfully processed {len(completed_descriptions)} components")
        return descriptions

    except Exception as e:
        logger.error(f"Error processing components directory: {str(e)}")
        return None


if __name__ == "__main__":
    input_directory = "codes"
    output_file = "component_descriptions2.json"
    descriptions = process_components_directory(input_directory, output_file)
