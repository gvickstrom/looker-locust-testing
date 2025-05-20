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

def process_attributes(
    command_line_attributes: Optional[List[str]] = None,
    csv_path: Optional[str] = None
) -> List[str]:
    """
    Process both command-line attributes and CSV attributes.
    Command-line attributes take precedence over CSV attributes.
    
    Returns a list of attribute strings in "name:value" format.
    """
    final_attributes = []
    user_attributes_dict = {}
    
    # Process attributes from CSV if provided
    if csv_path:
        user_attributes_dict = load_user_attributes_from_csv(csv_path)
        print(f"Loaded attributes from CSV: {user_attributes_dict}")
    
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