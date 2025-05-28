# Attempt 1: Using pyaspeller for Japanese (and other languages)
# Needs: pip install pyaspeller
# This library uses the Yandex Speller API and requires internet access.

from pyaspeller import YandexSpeller
import re

def correct_misspellings_pyaspeller(text: str, lang: str = 'ja') -> str:
    """
    Corrects misspellings in the text using YandexSpeller API.
    Supports multiple languages, including Japanese ('ja').
    Requires internet connection.
    """
    try:
        speller = YandexSpeller()
        # YandexSpeller checks word by word if passed a string.
        # It can handle up to 10000 characters per request.
        # For longer texts, it's better to split or ensure it handles it.
        # The library seems to handle longer texts by chunking.

        # The API works best with plain text. We should be mindful of not sending markup or complex structures.
        # It's also important to handle cases where the API might return multiple suggestions
        # or no suggestions. For "obvious" typos, we take the first suggestion if available.

        corrected_text_parts = []
        # Process paragraph by paragraph or sentence by sentence to maintain structure
        # and avoid hitting potential API limits with single very long strings.
        # However, pyaspeller's check() method on a string seems to handle this.
        
        # Let's split text into words and check them. This might be less efficient than sending blocks.
        # The `speller.spell(text)` method in some versions or `speller.check(text)` returns a list of Error objects.
        
        # Using check_text method which directly returns corrected text
        # This is available in some forks/versions or implies a different usage pattern.
        # The documented way for `pyaspeller` is `speller.check(text)` returning errors.
        # Let's stick to the documented `check` method and reconstruct the text.

        changes = speller.check(text, lang=lang) # List of Error objects
        
        # Sort changes by their position in reverse order to avoid index shifts during replacement
        changes.sort(key=lambda x: x['pos'], reverse=True)
        
        corrected_list = list(text)
        for change in changes:
            if change['s']: # If there are suggestions
                original_word = text[change['pos'] : change['pos'] + change['len']]
                # For "obvious" correction, take the first suggestion.
                # Some changes might be stylistic (e.g. ё to е in Russian), not just spelling.
                # We assume the first suggestion is the primary correction.
                replacement = change['s'][0] 
                
                # Ensure case is handled reasonably: if original was capitalized, capitalize replacement.
                if original_word.istitle() and not replacement.istitle():
                    replacement = replacement.capitalize()
                elif original_word.isupper() and not replacement.isupper() and len(original_word) > 1 : # Avoid for single letter uppercase like 'A'
                     # Check if replacement is not already mixed case or uppercase
                    if not any(c.islower() for c in replacement):
                        replacement = replacement.upper()

                corrected_list[change['pos'] : change['pos'] + change['len']] = list(replacement)
        
        return "".join(corrected_list)

    except Exception as e:
        print(f"Could not use YandexSpeller (ensure internet connection and library installed): {e}")
        print("Falling back to no spell correction for this run.")
        return text # Return original text if pyaspeller fails


# Fallback: Using pyspellchecker for English
# Needs: pip install pyspellchecker
from spellchecker import SpellChecker

def correct_misspellings_pyspellchecker_en(text: str) -> str:
    """
    Corrects obvious English misspellings in the text using pyspellchecker.
    This is a fallback if a Japanese spellchecker is not available/feasible.
    """
    try:
        spell = SpellChecker(language='en')
        
        # Tokenize text into words. Using regex to preserve punctuation.
        words = re.findall(r"[\w']+|[.,!?;:]", text)
        corrected_words = []
        # Find unknown words. Ensure words are actual words before checking.
        # pyspellchecker expects a list of words, not punctuation.
        string_words = [word for word in words if word.isalpha() or "'" in word]
        misspelled_words = spell.unknown(string_words)


        for i, word in enumerate(words):
            if word in misspelled_words:
                correction = spell.correction(word)
                if correction and correction != word : # ensure correction is different
                    # Preserve case
                    if word.istitle():
                        correction = correction.capitalize()
                    elif word.isupper() and len(word) > 1: # Check if correction is not already mixed case
                        if not any(c.islower() for c in correction):
                             correction = correction.upper()
                    corrected_words.append(correction)
                else:
                    corrected_words.append(word) # No correction found or same as original
            else:
                corrected_words.append(word)
        
        # Reconstruct the text.
        output_text = ""
        for i, word in enumerate(corrected_words):
            # Smart spacing: no space before punctuation, or if it's the start of text,
            # or after certain opening punctuation.
            if word in [".", ",", "!", "?", ";", ":"] or \
               output_text == "" or \
               output_text.endswith(("'","(","[","{"," ","\n")): # Added space and newline to handle end of line
                output_text += word
            else:
                output_text += " " + word
        return output_text # Strip leading/trailing spaces if any were accidentally added by logic

    except Exception as e:
        print(f"Error during pyspellchecker processing: {e}")
        return text # Return original text on error

# Main function that decides which spellchecker to use
def correct_obvious_misspellings(text: str, language: str = 'ja') -> str:
    """
    Corrects obvious misspellings in the text.
    Attempts to use YandexSpeller for Japanese (lang='ja') or other languages.
    Falls back to pyspellchecker for English (lang='en') if YandexSpeller fails or lang='en'.
    """
    if language.lower() == 'ja':
        # Try pyaspeller for Japanese
        try:
            # Test if YandexSpeller can be initialized (might raise if misconfigured or network issues)
            _ = YandexSpeller() 
            print("Using YandexSpeller for spell correction.")
            return correct_misspellings_pyaspeller(text, lang=language)
        except Exception as e:
            print(f"YandexSpeller not available or failed for Japanese ({e}). Defaulting to no correction.")
            # Fallback to English if Japanese was explicitly requested but failed,
            # or if the user wants to be notified.
            # For now, just print and return text.
            return text # Return original if primary spellchecker fails
    
    elif language.lower() == 'en':
        print("Using pyspellchecker for English spell correction.")
        return correct_misspellings_pyspellchecker_en(text)
    
    else: # Other languages potentially supported by YandexSpeller
        try:
            _ = YandexSpeller()
            print(f"Using YandexSpeller for spell correction (lang={language}).")
            return correct_misspellings_pyaspeller(text, lang=language)
        except Exception as e:
            print(f"YandexSpeller not available or failed for lang {language} ({e}). Defaulting to no correction.")
            return text

# Needs: pip install textacy spacy
# Needs a spaCy model, e.g.: python -m spacy download ja_core_news_sm (for Japanese)
# or python -m spacy download en_core_web_sm (for English)

import textacy
import spacy # Import spacy to check for model availability

# Global cache for loaded spaCy models to avoid reloading them multiple times.
SPACY_MODELS_CACHE = {}

def get_spacy_model(lang: str = 'ja'):
    """Loads and returns a spaCy model, caching it for future use."""
    model_name = ""
    if lang == 'ja':
        model_name = 'ja_core_news_sm'
    elif lang == 'en':
        model_name = 'en_core_web_sm'
    else:
        print(f"Unsupported language for Spacy model: {lang}. Defaulting to English if available.")
        model_name = 'en_core_web_sm'

    if model_name in SPACY_MODELS_CACHE:
        if SPACY_MODELS_CACHE[model_name] is None: # Previously failed to load
            print(f"Skipping {model_name} as it previously failed to load.")
        return SPACY_MODELS_CACHE[model_name]

    try:
        print(f"Loading spaCy model: {model_name}...")
        nlp = spacy.load(model_name)
        SPACY_MODELS_CACHE[model_name] = nlp
        print(f"Successfully loaded {model_name}.")
        return nlp
    except OSError:
        print(f"Spacy model '{model_name}' not found. Please download it, e.g.:")
        print(f"python -m spacy download {model_name}")
        if model_name != 'en_core_web_sm':
            print("Attempting to fall back to 'en_core_web_sm'...")
            SPACY_MODELS_CACHE[model_name] = None 
            return get_spacy_model(lang='en')
        else:
            SPACY_MODELS_CACHE[model_name] = None # Mark as failed
            print("Failed to load 'en_core_web_sm' as well. Cannot proceed with spaCy-dependent tasks.")
            return None

def detect_potentially_awkward_phrases(text: str, lang: str = 'ja', top_n_keyterms: int = 10) -> list[dict]:
    """
    Identifies potentially noteworthy or "awkward" phrases using Textacy's keyterm extraction
    and by finding long noun chunks.
    "Awkwardness" is inferred from keyterm analysis or phrase length.
    Returns a list of dictionaries, each with "phrase", "reason", and "score".
    """
    results = []
    nlp_spacy = get_spacy_model(lang)

    if not nlp_spacy:
        print("Skipping awkward phrase detection as spaCy model could not be loaded.")
        return results

    try:
        if not text or len(text.strip()) < 20: 
            return results

        doc = textacy.make_spacy_doc(text, lang=nlp_spacy)
        keyterms_with_scores = list(textacy.extract.keyterms.sgrank(doc, topn=top_n_keyterms))

        for term, score in keyterms_with_scores:
            results.append({
                "phrase": term,
                "reason": f"Identified as a keyterm by Textacy (SGRank score: {score:.4f}).",
                "score": score
            })
        
        for nc in doc.noun_chunks:
            if len(nc.text.split()) > 5: 
                is_part_of_keyterm = False
                for res_item in results:
                    if nc.text in res_item["phrase"] or res_item["phrase"] in nc.text:
                        is_part_of_keyterm = True
                        break
                if not is_part_of_keyterm:
                    results.append({
                        "phrase": nc.text,
                        "reason": "Identified as a long noun chunk (potential complexity/awkwardness).",
                        "score": -1.0 
                    })
        
        results.sort(key=lambda x: x.get('score', -1.0), reverse=True)

    except Exception as e:
        print(f"Error during Textacy awkward phrase detection: {e}")
    
    return results

# list_keywords_pdf function to be added here
import re

def list_keywords_pdf(pdf_text_content: str, keywords: list[str]) -> list[dict]:
    """
    Finds occurrences of specified keywords in PDF text content and lists them with counts.
    The search is case-insensitive.
    
    Args:
        pdf_text_content (str): The text content extracted from the PDF.
        keywords (list[str]): A list of keywords to search for.

    Returns:
        list[dict]: A list of dictionaries, each containing:
                    - "keyword": The keyword found.
                    - "count": Number of times the keyword was found.
    """
    results = []
    if not keywords or not pdf_text_content:
        return results

    # Sort keywords by length (descending) to handle overlapping phrases if necessary,
    # though for simple counting it's less critical than for replacement.
    # Filter out empty keywords
    valid_keywords = [kw for kw in keywords if kw]
    if not valid_keywords:
        return results
        
    valid_keywords.sort(key=len, reverse=True)

    for keyword in valid_keywords:
        try:
            # Case-insensitive count
            # Ensure keyword is properly escaped for regex, especially if it contains special characters
            matches = re.findall(re.escape(keyword), pdf_text_content, re.IGNORECASE)
            if matches:
                results.append({
                    "keyword": keyword,
                    "count": len(matches)
                })
        except Exception as e:
            print(f"Error processing keyword '{keyword}': {e}")
            # Optionally, continue to next keyword or handle error differently
    
    return results

import re

def generate_placeholder_headings(text: str, min_para_length: int = 500, heading_level: int = 3) -> list[dict]:
    """
    Identifies long paragraphs and suggests that a heading might be needed.
    This is a placeholder for a more advanced heading generation system (e.g., using GPT-3).

    Args:
        text (str): The input text.
        min_para_length (int): Minimum character length for a paragraph to be considered for a heading.
        heading_level (int): The conceptual heading level (not used in placeholder, but for API consistency).

    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains:
                    - "original_paragraph": The long paragraph identified.
                    - "suggested_heading": A placeholder suggestion string.
                    - "level": The conceptual heading level.
    """
    results = []
    if not text:
        return results

    # Split into paragraphs. A simple split by one or more newlines.
    # More sophisticated paragraph splitting might be needed for complex texts.
    paragraphs = re.split(r'\n\s*\n+', text.strip()) # Split by blank lines (one or more newlines with optional whitespace)
    if len(paragraphs) <= 1 and '\n' in text: # Fallback if no blank lines, try single newline split
            paragraphs = text.strip().split('\n')


    for para in paragraphs:
        para_strip = para.strip()
        if len(para_strip) > min_para_length:
            results.append({
                "original_paragraph": para_strip,
                "suggested_heading": f"[Placeholder: Consider a H{heading_level} heading for this long paragraph (approx. {len(para_strip)} chars).]",
                "level": heading_level
            })
    
    return results
