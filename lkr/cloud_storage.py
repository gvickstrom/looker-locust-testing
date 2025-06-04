"""
Google Cloud Storage helper for downloading user attributes CSV
"""
import os
import csv
import tempfile
import logging
from typing import List, Dict, Any, Optional
from google.cloud import storage
import random
import threading

logger = logging.getLogger(__name__)

class UserAttributesManager:
    """Singleton pattern to ensure CSV is only downloaded once per process"""
    _instance: Optional['UserAttributesManager'] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, bucket_name: str, csv_file_name: str = "user_attributes.csv"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    print(f"DEBUG: Creating NEW UserAttributesManager instance for bucket: {bucket_name}")
                    cls._instance = super().__new__(cls)
        else:
            print(f"DEBUG: Reusing EXISTING UserAttributesManager instance")
        return cls._instance
    
    def __init__(self, bucket_name: str, csv_file_name: str = "user_attributes.csv"):
        # Only initialize once, even if __init__ is called multiple times
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    print(f"DEBUG: Initializing UserAttributesManager with bucket_name={bucket_name}, csv_file_name={csv_file_name}")
                    self.bucket_name = bucket_name
                    self.csv_file_name = csv_file_name
                    self.user_attributes = []
                    self._download_and_parse_csv()
                    UserAttributesManager._initialized = True
                else:
                    print("DEBUG: UserAttributesManager already initialized, skipping")
        else:
            print("DEBUG: UserAttributesManager already initialized, skipping")
    
    def _download_and_parse_csv(self):
        """Download CSV from GCS and parse user attributes - ONLY CALLED ONCE"""
        print(f"DEBUG: Starting CSV download from bucket: {self.bucket_name}")
        try:
            # Initialize GCS client
            print("DEBUG: Initializing GCS client...")
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(self.csv_file_name)
            
            print(f"DEBUG: Checking if blob exists: {self.csv_file_name}")
            if not blob.exists():
                print(f"ERROR: Blob {self.csv_file_name} does not exist in bucket {self.bucket_name}")
                return
            
            print(f"DEBUG: Blob exists, size: {blob.size} bytes")
            
            # Download to temporary file (Windows-compatible approach)
            import tempfile
            import os
            
            # Create temporary file without auto-delete
            temp_fd, temp_path = tempfile.mkstemp(suffix='.csv', text=True)
            print(f"DEBUG: Created temp file: {temp_path}")
            
            try:
                # Close the file descriptor so we can write to it
                os.close(temp_fd)
                
                # Download the blob to the temporary file
                print("DEBUG: Downloading blob to temp file...")
                blob.download_to_filename(temp_path)
                print("DEBUG: Download completed")
                
                # Parse CSV
                print("DEBUG: Parsing CSV...")
                with open(temp_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    self.user_attributes = list(reader)
                
                print(f"DEBUG: CSV parsing completed. Found {len(self.user_attributes)} rows")
                if self.user_attributes:
                    print(f"DEBUG: First row sample: {self.user_attributes[0]}")
                    print(f"DEBUG: Available columns: {list(self.user_attributes[0].keys())}")
            
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                    print("DEBUG: Temp file cleaned up")
                except OSError:
                    print("DEBUG: Could not clean up temp file")
            
            logger.info(f"Successfully loaded {len(self.user_attributes)} user attributes from GCS")
            print(f"SUCCESS: Successfully loaded {len(self.user_attributes)} user attributes from GCS")
            
        except Exception as e:
            error_msg = f"Error downloading/parsing CSV from GCS: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
            # Fallback to empty list or default values
            self.user_attributes = []
    
    def get_random_user_attributes(self) -> Dict[str, Any]:
        """Get random user attributes from the loaded CSV data"""
        if not self.user_attributes:
            print("WARNING: No user attributes available, returning empty dict")
            logger.warning("No user attributes available, returning empty dict")
            return {}
        
        selected = random.choice(self.user_attributes)
        print(f"DEBUG: Selected random user attributes: {selected}")
        return selected
    
    def get_user_attributes_by_index(self, index: int) -> Dict[str, Any]:
        """Get user attributes by specific index"""
        if not self.user_attributes or index >= len(self.user_attributes):
            print(f"WARNING: Invalid index {index}, returning empty dict")
            logger.warning(f"Invalid index {index}, returning empty dict")
            return {}
        
        selected = self.user_attributes[index]
        print(f"DEBUG: Selected user by index {index}: {selected}")
        return selected
    
    def get_attribute_value(self, user_attributes: Dict[str, Any], attribute_name: str, default_value: Any = None) -> Any:
        """Get specific attribute value with fallback"""
        return user_attributes.get(attribute_name, default_value)
    
    def get_total_users(self) -> int:
        """Get total number of users available"""
        return len(self.user_attributes)
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance - useful for testing"""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
            print("DEBUG: UserAttributesManager instance reset")