import os
from pathlib import Path


def delete_processed_pngs():
    # Base paths
    sections_path = Path("sections")
    codes_path = Path("codes")

    deleted_count = 0

    # Process each subdirectory in sections
    for section_dir in sections_path.iterdir():
        if section_dir.is_dir():  # Only process directories
            # Get corresponding code directory
            code_dir = codes_path / section_dir.name

            # Skip if corresponding code directory doesn't exist
            if not code_dir.exists():
                print(f"Skipping {section_dir.name}: No matching code directory")
                continue

            # Get list of HTML files (without extension) for this section
            processed_files = {f.stem for f in code_dir.glob("*.html")}

            # Delete corresponding PNGs
            for png_file in section_dir.glob("*.png"):
                if png_file.stem in processed_files:
                    png_file.unlink()  # Delete the file
                    deleted_count += 1
                    # print(f"Deleted: {section_dir.name}/{png_file.name}")

    print(f"\nTotal files deleted: {deleted_count}")


if __name__ == "__main__":
    # Ask for confirmation
    # confirm = input("This will delete processed PNG files. Continue? (y/n): ")
    # if confirm.lower() == "y":
    delete_processed_pngs()
    # else:
    # print("Operation cancelled")
