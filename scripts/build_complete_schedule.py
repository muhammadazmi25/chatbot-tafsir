import fitz
import re
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

# Target missing verses by Surah
MISSING = {
    11: [12, 14, 37, 41, 43, 47, 51, 56, 67, 68, 78, 79, 89, 90, 96, 97, 98, 102, 112, 114],
    12: [47, 54, 57, 59, 61, 62, 65, 69, 76, 77, 79, 96],
    16: [12, 18, 29, 90],
    17: [38],
    21: [69],
    23: [75],
    24: list(range(11, 65))
}

print(f"Total targets: {sum(len(v) for v in MISSING.values())} verses")
