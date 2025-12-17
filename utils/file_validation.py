# utils/file_validation.py
"""
File validation utilities.
"""

import os
from typing import Tuple, List, Optional

# Maximum file size: 50 MB
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Maximum total size: 200 MB
MAX_TOTAL_SIZE_MB = 200
MAX_TOTAL_SIZE_BYTES = MAX_TOTAL_SIZE_MB * 1024 * 1024


def validate_file_size(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate file size.
    Returns (is_valid, error_message)
    """
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    file_size = os.path.getsize(file_path)
    
    if file_size == 0:
        return False, "File is empty"
    
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return False, f"File too large ({size_mb:.1f} MB). Maximum size is {MAX_FILE_SIZE_MB} MB"
    
    return True, None


def validate_files(file_paths: List[str]) -> Tuple[bool, List[str], Optional[str]]:
    """
    Validate multiple files.
    Returns (is_valid, valid_files, error_message)
    """
    valid_files = []
    errors = []
    total_size = 0
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            errors.append(f"{os.path.basename(file_path)}: File not found")
            continue
        
        # Check individual file size
        is_valid, error = validate_file_size(file_path)
        if not is_valid:
            errors.append(f"{os.path.basename(file_path)}: {error}")
            continue
        
        file_size = os.path.getsize(file_path)
        
        # Check total size
        if total_size + file_size > MAX_TOTAL_SIZE_BYTES:
            errors.append(
                f"{os.path.basename(file_path)}: Total size would exceed {MAX_TOTAL_SIZE_MB} MB limit"
            )
            continue
        
        valid_files.append(file_path)
        total_size += file_size
    
    if not valid_files:
        error_msg = "No valid files found. " + "; ".join(errors) if errors else "No files provided"
        return False, [], error_msg
    
    if errors:
        error_msg = "Some files were skipped: " + "; ".join(errors)
        return True, valid_files, error_msg
    
    return True, valid_files, None




