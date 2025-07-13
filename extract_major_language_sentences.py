#!/usr/bin/env python3
"""
Extract sentences for major world languages from UDHR dataset.
This script extracts approximately 50 sentences for each major language.
"""

import os
import json
import re

def clean_sentence(sentence):
    """Clean and normalize a sentence."""
    # Remove extra whitespace
    sentence = re.sub(r'\s+', ' ', sentence.strip())
    # Remove empty lines
    if not sentence or sentence.isspace():
        return None
    # Skip very short sentences (likely headers or numbers)
    if len(sentence) < 10:
        return None
    # Skip lines that are likely headers or article numbers
    if re.match(r'^(Article|Artículo|Article premier|Artículo \d+|Preamble|Préambule|Universal Declaration|Declaración Universal|Declaração Universal|Déclaration universelle)', sentence, re.IGNORECASE):
        return None
    # Skip lines that are just numbers or very short
    if re.match(r'^\d+$', sentence):
        return None
    # Skip lines that are just "Now, therefore," or similar
    if re.match(r'^(Now, therefore|L\'Assemblée générale|La Asamblea General|A Assembléia Geral)', sentence, re.IGNORECASE):
        return None
    return sentence

def extract_sentences_from_file(filepath, max_sentences=50):
    """Extract sentences from a UDHR file."""
    sentences = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split by lines and clean
        lines = content.split('\n')
        for line in lines:
            sentence = clean_sentence(line)
            if sentence:
                sentences.append(sentence)
                if len(sentences) >= max_sentences:
                    break
    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []
    
    return sentences

def main():
    # Major languages and their corresponding UDHR files
    major_languages = {
        'english': 'udhr/English-Latin1',
        'spanish': 'udhr/Spanish-Latin1',
        'french': 'udhr/French_Francais-Latin1',
        'portuguese': 'udhr/Portuguese_Portugues-Latin1',
        'russian': 'udhr/Russian-Cyrillic',
        'chinese': 'udhr/Chinese_Mandarin-UTF8',
        'hindi': 'udhr/Hindi_web-UTF8',
        'bengali': 'udhr/Bengali-UTF8',
        'german': 'udhr/German_Deutsch-Latin1',
        'japanese': 'udhr/Japanese_Nihongo-UTF8',
        'italian': 'udhr/Italian-Latin1',
        'turkish': 'udhr/Turkish_Turkce-UTF8',
        'vietnamese': 'udhr/Vietnamese-UTF8',
        'korean': 'udhr/Korean_Hankuko-UTF8',
        'persian': 'udhr/Farsi_Persian-UTF8',
        'swahili': 'udhr/Swahili_Kiswahili-Latin1',
        'indonesian': 'udhr/Indonesian-Latin1'
    }
    
    # Extract sentences for each language
    all_sentences = {}
    
    for lang_name, filepath in major_languages.items():
        print(f"Processing {lang_name}...")
        
        if os.path.exists(filepath):
            sentences = extract_sentences_from_file(filepath, max_sentences=50)
            if sentences:
                all_sentences[lang_name] = sentences
                print(f"  Extracted {len(sentences)} sentences")
            else:
                print(f"  No sentences extracted")
        else:
            print(f"  File not found: {filepath}")
    
    # Save to JSON file
    output_file = 'udhr_major_languages_sentences_extended.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_sentences, f, ensure_ascii=False, indent=2)
    
    print(f"\nExtracted sentences for {len(all_sentences)} languages")
    print(f"Results saved to {output_file}")
    
    # Print summary
    print("\nSummary:")
    for lang_name, sentences in all_sentences.items():
        print(f"  {lang_name}: {len(sentences)} sentences")

if __name__ == "__main__":
    main() 