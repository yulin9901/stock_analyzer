#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import os
import importlib.util

CONFIG_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.py.template")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.py")

def load_config():
    """Loads configuration from config.py.
    If config.py does not exist, it guides the user to create it from config.py.template.
    """
    if not os.path.exists(CONFIG_PATH):
        print(f"Configuration file {CONFIG_PATH} not found.")
        if os.path.exists(CONFIG_TEMPLATE_PATH):
            print(f"Please copy {CONFIG_TEMPLATE_PATH} to {CONFIG_PATH} and fill in your details.")
        else:
            print(f"Critical: Configuration template {CONFIG_TEMPLATE_PATH} is also missing.")
        raise FileNotFoundError(f"Configuration file {CONFIG_PATH} is missing. Please create it from the template.")

    try:
        spec = importlib.util.spec_from_file_location("config", CONFIG_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for configuration file {CONFIG_PATH}")

        app_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_config)

        # Check for placeholder values and issue warnings
        if getattr(app_config, "TIANAPI_KEY", "") == "YOUR_TIANAPI_KEY_HERE":
            print("Warning: TIANAPI_KEY is a placeholder in config.py. TianAPI calls may fail or use a demo key.")
        if getattr(app_config, "OPENAI_API_KEY", "") == "YOUR_OPENAI_API_KEY_HERE":
            print("Warning: OPENAI_API_KEY is a placeholder in config.py. ChatGPT calls will be simulated or fail.")
        if getattr(app_config, "DB_USER", "") == "your_db_user":
            print("Warning: DB_USER is a placeholder in config.py. Database operations may fail.")

        return app_config
    except Exception as e:
        print(f"Error loading configuration from {CONFIG_PATH}: {e}")
        raise

# Example of DB config dictionary expected by modules
def get_db_config(config):
    return {
        "DB_HOST": config.DB_HOST,
        "DB_PORT": config.DB_PORT,
        "DB_USER": config.DB_USER,
        "DB_PASSWORD": config.DB_PASSWORD,
        "DB_NAME": config.DB_NAME
    }

if __name__ == "__main__":
    print("Attempting to load configuration...")
    try:
        cfg = load_config()
        print("Configuration loaded successfully.")
        print(f"DB Host: {cfg.DB_HOST}")
        print(f"TianAPI Key: {'*' * len(cfg.TIANAPI_KEY) if cfg.TIANAPI_KEY != 'YOUR_TIANAPI_KEY_HERE' else cfg.TIANAPI_KEY}")
        db_params = get_db_config(cfg)
        print(f"DB Params for modules: {db_params}")
    except Exception as e:
        print(f"Failed to load or use configuration: {e}")

