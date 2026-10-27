import re

def normalize_ocr_numbers(s):
    # Map common OCR character substitutions for digits
    # Only in bracketed or citation contexts
    sub_map = {
        'l': '1', 'i': '1', 'I': '1', 'L': '1', '|': '1', '!': '1',
        'o': '0', 'O': '0', 'Q': '0',
        'z': '2', 'Z': '2',
        's': '5', 'S': '5',
        'b': '6', # only rarely, be careful
    }
    
    # We want to match: (Qs. <Surah> [<chap>]: <verse>)
    # Normalize:
    # 1. Clean surah name
    # 2. Extract chapter and verse
    pass
