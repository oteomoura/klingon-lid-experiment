#!/usr/bin/env python3
"""
Utility functions for language identification experiments.
"""

import json
import fasttext
from huggingface_hub import hf_hub_download
from collections import Counter, defaultdict
import statistics

def load_model():
    """Load the GlotLID model."""
    model_path = hf_hub_download(repo_id="cis-lmu/glotlid", filename="model.bin", cache_dir=None)
    return fasttext.load_model(model_path)

def load_sentences(filename):
    """Load sentences from a JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_detailed_results(results, language_stats, filename='experiment_results.json'):
    """Save detailed experiment results to JSON file."""
    output_data = {
        'results': results,
        'language_stats': language_stats,
        'summary': {
            'total_languages': len(language_stats),
            'average_accuracy': statistics.mean([stats['accuracy'] for stats in language_stats.values()]),
            'median_accuracy': statistics.median([stats['accuracy'] for stats in language_stats.values()]),
            'min_accuracy': min([stats['accuracy'] for stats in language_stats.values()]),
            'max_accuracy': max([stats['accuracy'] for stats in language_stats.values()])
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Detailed results saved to {filename}")

def generate_script_variants(lang_code):
    """Generate all possible script variant labels for a language code."""
    scripts = [
        'Latn', 'Cyrl', 'Arab', 'Deva', 'Thai', 'Hang', 'Hira', 'Kana', 
        'Hans', 'Hant', 'Hani', 'Jpan', 'Ethi', 'Grek', 'Hebr', 'Beng', 'Gujr', 'Guru',
        'Knda', 'Mlym', 'Orya', 'Taml', 'Telu', 'Tibt', 'Geor', 'Armn',
        'Khmr', 'Laoo', 'Mymr', 'Sinh', 'Mong', 'Copt', 'Syrc', 'Thaa',
        'Nkoo', 'Vaii', 'Bamu', 'Lana', 'Talu', 'Bass', 'Aghb', 'Cakm',
        'Cham', 'Dupl', 'Egyp', 'Elba', 'Gran', 'Hmng', 'Khar', 'Khoj',
        'Kits', 'Lina', 'Mahj', 'Mani', 'Mend', 'Modi', 'Mroo', 'Mult',
        'Narb', 'Nbat', 'Nshu', 'Orkh', 'Osge', 'Osma', 'Palm', 'Pauc',
        'Phag', 'Phnx', 'Plrd', 'Rjng', 'Rohg', 'Saur', 'Sgnw', 'Shaw',
        'Shrd', 'Sidd', 'Sind', 'Sogd', 'Sogo', 'Soyo', 'Sund', 'Sylo',
        'Tagb', 'Takr', 'Tale', 'Tavt', 'Tfng', 'Tglg', 'Tirh', 'Ugar',
        'Wara', 'Yiii', 'Zanb', 'Zinh', 'Zmth', 'Zsye', 'Zsym', 'Zxxx',
        'Zyyy', 'Zzzz', 'Cans'
    ]
    
    variants = [f"__label__{lang_code}"]  # Base variant
    for script in scripts:
        variants.append(f"__label__{lang_code}_{script}")
    
    return variants

def analyze_results(results):
    """Analyze experiment results and return statistics."""
    language_stats = {}
    
    for lang_code, lang_results in results.items():
        total_sentences = len(lang_results['predictions'])
        correct_predictions = lang_results['correct_predictions']
        klingon_predictions = lang_results['klingon_predictions']
        
        accuracy = (correct_predictions / total_sentences) * 100 if total_sentences > 0 else 0
        klingon_rate = (klingon_predictions / total_sentences) * 100 if total_sentences > 0 else 0
        
        # Get most common misclassifications
        other_predictions = lang_results['other_predictions']
        most_common_misclassifications = other_predictions.most_common(5)
        
        language_stats[lang_code] = {
            'total_sentences': total_sentences,
            'correct_predictions': correct_predictions,
            'accuracy': accuracy,
            'klingon_predictions': klingon_predictions,
            'klingon_rate': klingon_rate,
            'most_common_misclassifications': most_common_misclassifications,
            'average_confidence': statistics.mean(lang_results['confidences']) if lang_results['confidences'] else 0
        }
    
    return language_stats

def print_accuracy_table(language_stats, title="Accuracy Table"):
    """Print a formatted accuracy table."""
    print(f"\n=== {title} ===")
    print(f"{'Rank':<4} {'Language':<20} {'Code':<10} {'Accuracy':<10} {'Correct/Total':<15} {'Klingon Rate':<12}")
    print("-" * 85)
    
    # Sort by accuracy (descending)
    sorted_stats = sorted(language_stats.items(), key=lambda x: x[1]['accuracy'], reverse=True)
    
    for rank, (lang_code, stats) in enumerate(sorted_stats, 1):
        accuracy = stats['accuracy']
        correct = stats['correct_predictions']
        total = stats['total_sentences']
        klingon_rate = stats['klingon_rate']
        
        print(f"{rank:<4} {lang_code:<20} {'':<10} {accuracy:>6.1f}%    {correct:>3}/{total:<3}        {klingon_rate:>6.1f}%")

def get_language_code_mapping():
    """Get the mapping from our language codes to GlotLID codes."""
    return {
        'man': 'msc',  # Maninka -> Sankaran Maninka
        'amc': 'kaq',  # Amahuaca -> Kaqchikel (or similar)
        'hva': 'hus',  # Huasteco -> Huasteco (hus_Latn)
        'nah': 'nch',  # Nahuatl -> Nahuatl (nch_Latn)
        'nym': 'suk',  # Kinyamwezi -> Sukuma (suk_Latn)
        'mix': 'xtm',  # Mixtec -> Mixtec (xtm_Latn)
        'lns': 'vut',  # Lamnso -> Vute (vut_Latn)
        'huu': 'huu',  # Huitoto Murui
        'quc': 'quc',  # K'iche'
        'mam': 'mam',  # Mam
        'arn': 'arn',  # Mapudungun
        'yua': 'yua',  # Yucatec Maya
        'maz': 'maz',  # Mazahua
        'nav': 'nav',  # Navajo
        'not': 'not',  # Nomatsiguenga
        'amr': 'amr',  # Amarakaeri
        'ame': 'ame',  # Amuesha
        'cni': 'cni',  # Asháninka
        'agr': 'agr',  # Aguaruna
        'acu': 'acu',  # Achuar
        'arl': 'arl',  # Arabela
        'lun': 'lun',  # Lunda
        'lue': 'lue',  # Luvale
        'nba': 'nba',  # Ngangela
        'kde': 'kde',  # Makonde
        'men': 'men',  # Mende
        'lia': 'lia',  # Limba
        'kpe': 'kpe',  # Kpelewo
        'mad': 'mad',  # Madurese
        'min': 'min',  # Minangkabau
        'mic': 'mic',  # Mi'kmaq
        'mcf': 'mcf',  # Matsés
        'miq': 'miq',  # Miskito
        'ido': 'ido',  # Ido
        'ina': 'ina',  # Interlingua
        'kal': 'kal',  # Greenlandic
        'kri': 'kri',  # Krio
        'pcm': 'pcm',  # Nigerian Pidgin
        'klingon': 'tlh',  # Klingon
    }

def load_language_names():
    """Load language names from JSON file."""
    try:
        with open('language_names.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: language_names.json not found. Using default names.")
        return {}

def load_language_categories():
    """Load language categories from JSON file."""
    try:
        with open('language_categories.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: language_categories.json not found. Using default categories.")
        return {} 