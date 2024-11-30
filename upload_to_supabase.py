import os
from pathlib import Path
import json
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def read_component_file(file_path: Path) -> Optional[str]:
    """Read component HTML code from file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return None


def upload_section_components(
    section_type: str, components: list[dict]
) -> Optional[Dict[str, Any]]:
    """Upload all components from a section in one batch"""
    try:
        result = supabase.table("components").insert(components).execute()
        logger.info(f"Uploaded {len(components)} components for section {section_type}")
        return result.data

    except Exception as e:
        logger.error(f"Error uploading section {section_type}: {str(e)}")
        return None


def process_components(codes_dir: str, descriptions_file: str):
    """Process and upload components by section"""
    try:
        # Load descriptions
        with open(descriptions_file, "r", encoding="utf-8") as f:
            descriptions = json.load(f)

        base_path = Path(codes_dir)
        uploaded_sections = 0
        error_sections = 0
        total_components = 0

        # Process each section
        for section_folder in base_path.iterdir():
            if not section_folder.is_dir():
                continue

            section_type = section_folder.name
            section_descriptions = descriptions.get(section_type, {})
            section_components = []

            # Collect all components for this section
            for html_file in section_folder.glob("*.html"):
                component_id = html_file.stem

                # Skip if no description available
                if component_id not in section_descriptions:
                    logger.warning(
                        f"No description found for {section_type}/{component_id}"
                    )
                    continue

                # Read component code
                code = read_component_file(html_file)
                if not code:
                    continue

                # Create component data
                formatted_component_id = f"{section_type.lower()}-{component_id}"
                component_data = {
                    "section_type": section_type,
                    "component_id": formatted_component_id,
                    "code": code,
                    "description": section_descriptions[component_id],
                    "is_active": True,
                }
                section_components.append(component_data)

            # Upload section components in batch
            if section_components:
                result = upload_section_components(section_type, section_components)
                if result:
                    uploaded_sections += 1
                    total_components += len(section_components)
                    logger.info(
                        f"Successfully uploaded section: {section_type} with {len(section_components)} components"
                    )
                else:
                    error_sections += 1
                    logger.error(f"Failed to upload section: {section_type}")

        logger.info(
            f"Upload complete. Successful sections: {uploaded_sections}, Failed sections: {error_sections}"
        )
        logger.info(f"Total components uploaded: {total_components}")
        return uploaded_sections, error_sections, total_components

    except Exception as e:
        logger.error(f"Error processing components: {str(e)}")
        return 0, 0, 0


# def check_existing_component(section_type: str, component_id: str) -> bool:
#     """Check if component already exists in Supabase"""
#     try:
#         result = (
#             supabase.table("components")
#             .select("id")
#             .eq("section_type", section_type)
#             .eq("component_id", component_id)
#             .execute()
#         )

#         return len(result.data) > 0
#     except Exception as e:
#         logger.error(f"Error checking existing component: {str(e)}")
#         return False


if __name__ == "__main__":
    codes_directory = "codes"
    descriptions_file = "component_descriptions2.json"

    uploaded_sections, failed_sections, total_uploaded = process_components(
        codes_directory, descriptions_file
    )
    logger.info(
        f"Upload summary - Successful sections: {uploaded_sections}, Failed sections: {failed_sections}"
    )
    logger.info(f"Total components uploaded: {total_uploaded}")
