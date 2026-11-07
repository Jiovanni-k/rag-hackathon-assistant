"""Arabic text normalisation.

clean_text()   -> light, safe changes applied to stored text (still nice to read).
normalize()    -> aggressive folding used only for keyword matching (BM25), so that
                  «أسجّل» / «اسجل» and «الجامعة» / «الجامعه» match each other.
"""
import re
import unicodedata

TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
TATWEEL = "ـ"
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
WORD = re.compile(r"\w+")

# Very common words that carry no meaning for search (Arabic, dialect, English).
STOPWORDS = set("""
في من على الى عن مع او ان هل ما ماذا متى كيف كم لماذا هو هي انا انت نحن هذا هذه ذلك التي الذي
شو ايش اللي بدي عشان لازم بقدر اقدر يعني كمان هاد هاي مين وين امتى ليش اذا لو بس يا
the a an of to in on for and or is are be can i my do does what how when which who with at by from
""".split())


def clean_text(text):
    """Fix PDF artefacts without changing meaning."""
    text = unicodedata.normalize("NFKC", text)      # presentation forms ﺍﻟﻄﺐ -> الطب, ligatures
    text = text.replace(TATWEEL, "").replace(" ", " ")
    text = TASHKEEL.sub("", text)
    text = text.translate(DIGITS)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize(text):
    """Aggressive folding for matching only."""
    return clean_text(text).translate(FOLD).lower()


def tokenize(text):
    """Words for BM25: normalised, stopwords removed, Arabic prefixes «ال/و/ب» stripped."""
    tokens = []
    for word in WORD.findall(normalize(text)):
        if word in STOPWORDS:
            continue
        for prefix in ("وال", "بال", "لل", "ال"):
            if word.startswith(prefix) and len(word) - len(prefix) >= 3:
                word = word[len(prefix):]
                break
        tokens.append(word)
    return tokens
