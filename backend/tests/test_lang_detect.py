"""langdetect smoke tests — pure-function, no network."""

from app.services.lang_detect import detect_language


def test_detect_english() -> None:
    text = "The quick brown fox jumps over the lazy dog. It was a sunny day in June."
    assert detect_language(text) == "en"


def test_detect_hindi() -> None:
    text = "नमस्ते दुनिया, यह एक हिंदी पाठ है। आप कैसे हैं? मुझे यह पुस्तक पसंद है।"
    assert detect_language(text) == "hi"


def test_detect_tamil() -> None:
    text = "வணக்கம் உலகம், இது தமிழில் உள்ள ஒரு உரை. நீங்கள் எப்படி இருக்கிறீர்கள்?"
    assert detect_language(text) == "ta"


def test_detect_bengali() -> None:
    text = "নমস্কার বিশ্ব, এটি একটি বাংলা পাঠ্য। আপনি কেমন আছেন?"
    assert detect_language(text) == "bn"


def test_detect_too_short_returns_none() -> None:
    assert detect_language("hi") is None
    assert detect_language("") is None
    assert detect_language("   ") is None


def test_detect_is_deterministic() -> None:
    text = "This is a moderately long English sentence used to test determinism."
    assert detect_language(text) == detect_language(text)
