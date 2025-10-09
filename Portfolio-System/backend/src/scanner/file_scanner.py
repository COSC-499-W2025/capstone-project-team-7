# scanner/file_scanner.py
# Core artifact discovery.
# - Walk through extracted .zip directory
# - Use zipfile + pathlib to parse files
# - Extract metadata (file name, size, creation date)
# - Use python-magic to verify file types
