import sys
import os

# Make the backend root importable so `from graphs...` / `from models...` resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env so ChatGoogleGenerativeAI module-level init doesn't raise on import
from dotenv import load_dotenv
load_dotenv()
