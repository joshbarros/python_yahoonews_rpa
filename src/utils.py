import json
import os

def load_work_item(config_path):
    """
    Load a work item configuration from a JSON file.

    Args:
        config_path (str): The file path to the JSON configuration file.

    Returns:
        dict: The configuration data loaded from the JSON file.
    
    Raises:
        FileNotFoundError: If the file at config_path does not exist.
        json.JSONDecodeError: If the file content is not a valid JSON.
    """
    with open(config_path, "r") as file:
        return json.load(file)

def get_config():
    """
    Retrieve the configuration for the RPA process.

    This method attempts to load the configuration from a JSON file. The
    path to the configuration file is determined by the environment variable
    'ROBOT_CONFIG'. If this environment variable is not set, it defaults to 
    'devdata/workitems/work-item.json'.

    Returns:
        dict: The configuration data loaded from the JSON file.
    
    Raises:
        FileNotFoundError: If the file at the resolved config_path does not exist.
        json.JSONDecodeError: If the file content is not a valid JSON.
    """
    config_path = os.getenv("ROBOT_CONFIG", "devdata/workitems/work-item.json")
    return load_work_item(config_path)
