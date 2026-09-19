"""
Configuration settings for AeroResolve AI.
Model: gemini-2.5-flash-lite
"""
import os
from dotenv import load_dotenv

# Load .env from project root (safe no-op if file is missing)
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
