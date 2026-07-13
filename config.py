# config.py

from google import genai

MODEL = "gemini-2.5-flash"


def get_client(api_key):
    return genai.Client(api_key=api_key)