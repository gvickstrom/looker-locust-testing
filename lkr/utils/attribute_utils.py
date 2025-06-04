import csv
import os
import random
from typing import Dict, List, Optional

def load_user_attributes_from_csv(csv_path: str) -> Dict[str, List[str]]:
    """
    Load user attributes from a CSV file where the first row contains
    attribute names and subsequent rows contain possible values.
    Returns a dictionary of attribute names to lists of possible values.
    """
    attributes = {}
    
    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"Warning: User attributes CSV file not found: {csv_path}")
        return attributes
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            
            # First row contains attribute names
            header = next(reader, None)
            if not header:
                print("Warning: CSV file is empty.")
                return attributes
            
            # Initialize dictionary entries for each attribute
            for attr_name in header:
                attr_name = attr_name.strip()
                if attr_name:  # Skip empty column names
                    attributes[attr_name] = []
            
            # Process data rows
            for row in reader:
                # Map each value to its corresponding attribute
                for i, value in enumerate(row):
                    if i < len(header) and header[i].strip() in attributes:
                        value = value.strip()
                        if value:  # Skip empty values
                            attributes[header[i].strip()].append(value)
    
    except Exception as e:
        print(f"Error loading user attributes from CSV: {str(e)}")
    
    return attributes

def process_attributes_with_cloud_storage(
    command_line_attributes: Optional[List[str]] = None,
    csv_path: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> List[str]:
    """
    Process attributes from command line, local CSV, or cloud storage CSV.
    Priority: command-line > local CSV > cloud storage CSV
    
    Returns a list of attribute strings in "name:value" format.
    """
    print(f"DEBUG: process_attributes_with_cloud_storage called")
    print(f"DEBUG: command_line_attributes = {command_line_attributes}")
    print(f"DEBUG: csv_path = {csv_path}")
    print(f"DEBUG: bucket_name = {bucket_name}")
    
    final_attributes = []
    user_attributes_dict = {}
    
    # Try local CSV first if provided
    if csv_path:
        print(f"DEBUG: Using local CSV path: {csv_path}")
        user_attributes_dict = load_user_attributes_from_csv(csv_path)
        print(f"Loaded attributes from local CSV: {user_attributes_dict}")
    
    # If no local CSV and bucket name provided, try cloud storage
    elif bucket_name:
        print(f"DEBUG: Trying cloud storage with bucket: {bucket_name}")
        try:
            print("DEBUG: Importing UserAttributesManager...")
            from lkr.cloud_storage import UserAttributesManager
            print("DEBUG: Creating UserAttributesManager instance...")
            manager = UserAttributesManager(bucket_name)
            print(f"DEBUG: Manager created, user_attributes length: {len(manager.user_attributes)}")
            
            if manager.user_attributes:
                print("DEBUG: Processing user attributes from cloud storage...")
                # Convert cloud storage CSV format to the expected dictionary format
                for attr_name in manager.user_attributes[0].keys():
                    user_attributes_dict[attr_name] = []
                print(f"DEBUG: Initialized attribute dictionary with keys: {list(user_attributes_dict.keys())}")
                
                # Collect all unique values for each attribute
                for user_data in manager.user_attributes:
                    for attr_name, value in user_data.items():
                        if value and str(value) not in user_attributes_dict[attr_name]:
                            user_attributes_dict[attr_name].append(str(value))
                            
                print(f"DEBUG: Loaded attributes from cloud storage: {user_attributes_dict}")
            else:
                print("DEBUG: No user attributes found in manager")
        except Exception as e:
            print(f"ERROR: Could not load CSV from cloud storage: {e}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
    else:
        print("DEBUG: No CSV path or bucket name provided")
    
    # Process manually specified attributes first
    if command_line_attributes:
        print(f"DEBUG: Processing command line attributes: {command_line_attributes}")
        for attr in command_line_attributes:
            final_attributes.append(attr)
    else:
        print("DEBUG: No command line attributes provided")
    
    # Extract already specified attribute names
    specified_attrs = set()
    for attr in final_attributes:
        if ":" in attr:
            name, _ = attr.split(":", 1)
            specified_attrs.add(name)
    print(f"DEBUG: Already specified attributes: {specified_attrs}")
    
    # Add random attributes from CSV for each one that's not already specified
    print(f"DEBUG: Available CSV attributes: {list(user_attributes_dict.keys())}")
    for attr_name in user_attributes_dict:
        if attr_name not in specified_attrs:
            values = user_attributes_dict[attr_name]
            if values:
                value = random.choice(values)
                final_attributes.append(f"{attr_name}:{value}")
                print(f"DEBUG: Added CSV attribute: {attr_name}:{value}")
    
    print(f"DEBUG: Final attributes: {final_attributes}")
    return final_attributes

def process_attributes_with_cloud_storage(
    command_line_attributes: Optional[List[str]] = None,
    csv_path: Optional[str] = None,
    bucket_name: Optional[str] = None
) -> List[str]:
    """
    Process attributes from command line, local CSV, or cloud storage CSV.
    Priority: command-line > local CSV > cloud storage CSV
    
    Returns a list of attribute strings in "name:value" format.
    """
    final_attributes = []
    user_attributes_dict = {}
    
    # Try local CSV first if provided
    if csv_path:
        user_attributes_dict = load_user_attributes_from_csv(csv_path)
        print(f"Loaded attributes from local CSV: {user_attributes_dict}")
    
    # If no local CSV and bucket name provided, try cloud storage
    elif bucket_name:
        try:
            from lkr.cloud_storage import UserAttributesManager
            manager = UserAttributesManager(bucket_name)
            if manager.user_attributes:
                # Convert cloud storage CSV format to the expected dictionary format
                for attr_name in manager.user_attributes[0].keys():
                    user_attributes_dict[attr_name] = []
                
                # Collect all unique values for each attribute
                for user_data in manager.user_attributes:
                    for attr_name, value in user_data.items():
                        if value and str(value) not in user_attributes_dict[attr_name]:
                            user_attributes_dict[attr_name].append(str(value))
                            
                print(f"Loaded attributes from cloud storage: {user_attributes_dict}")
        except Exception as e:
            print(f"Warning: Could not load CSV from cloud storage: {e}")
    
    # Process manually specified attributes first
    if command_line_attributes:
        for attr in command_line_attributes:
            final_attributes.append(attr)
    
    # Extract already specified attribute names
    specified_attrs = set()
    for attr in final_attributes:
        if ":" in attr:
            name, _ = attr.split(":", 1)
            specified_attrs.add(name)
    
    # Add random attributes from CSV for each one that's not already specified
    for attr_name in user_attributes_dict:
        if attr_name not in specified_attrs:
            values = user_attributes_dict[attr_name]
            if values:
                value = random.choice(values)
                final_attributes.append(f"{attr_name}:{value}")
    
    print(f"Final attributes: {final_attributes}")
    return final_attributes