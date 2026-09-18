"""
Configuration settings for AeroResolve AI.
Model: gemini-3.1-flash-lite
"""
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
