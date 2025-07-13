#!/usr/bin/env python3
"""
Language Identification Experiment: Low-Resource vs Major Languages

This script runs comprehensive language identification experiments comparing
the performance of the GlotLID model on low-resource languages vs major languages,
with a focus on Klingon misclassification patterns.
"""

import json
from collections import Counter
import statistics
from utils import (
    load_model, load_sentences, save_detailed_results, analyze_results,
    print_accuracy_table, generate_script_variants, get_language_code_mapping,
    load_language_names, load_language_categories
)

def classify_sentences(model, sentences_dict, code_mapping=None):
    """Classify all sentences and return results."""
    if code_mapping is None:
        code_mapping = get_language_code_mapping()
    
    results = {}
    
    for lang_code, sentences in sentences_dict.items():
        print(f"Classifying {lang_code} ({len(sentences)} sentences)...")
        lang_results = {
            'predictions': [],
            'confidences': [],
            'correct_predictions': 0,
            'klingon_predictions': 0,
            'other_predictions': Counter()
        }
        
        # Get the actual GlotLID code for this language
        glotlid_code = code_mapping.get(lang_code, lang_code)
        
        # Generate all possible script variants for this language
        correct_label_variants = generate_script_variants(glotlid_code)
        
        for sentence in sentences:
            try:
                labels, probabilities = model.predict(sentence, k=1)
                predicted_label = labels[0]
                confidence = probabilities[0]
                
                lang_results['predictions'].append(predicted_label)
                lang_results['confidences'].append(confidence)
                
                # Check if correctly classified
                if predicted_label in correct_label_variants:
                    lang_results['correct_predictions'] += 1
                # Check if misclassified as Klingon
                elif predicted_label == "__label__tlh_Latn":
                    lang_results['klingon_predictions'] += 1
                else:
                    lang_results['other_predictions'][predicted_label] += 1
                    
            except Exception as e:
                print(f"Error classifying sentence in {lang_code}: {e}")
                continue
        
        results[lang_code] = lang_results
    
    return results

def run_low_resource_experiment():
    """Run experiment on low-resource languages."""
    print("\n=== LOW-RESOURCE LANGUAGES EXPERIMENT ===")
    
    # Load sentences
    sentences_dict = load_sentences('udhr_low_resource_sentences.json')
    print(f"Loaded {len(sentences_dict)} low-resource languages.")
    
    # Load model
    model = load_model()
    
    # Run classification
    results = classify_sentences(model, sentences_dict)
    
    # Analyze results
    language_stats = analyze_results(results)
    
    # Print results
    print_accuracy_table(language_stats, "Low-Resource Languages Results")
    
    # Save results
    save_detailed_results(results, language_stats, 'low_resource_results.json')
    
    return results, language_stats

def run_major_languages_experiment():
    """Run experiment on major world languages."""
    print("\n=== MAJOR WORLD LANGUAGES EXPERIMENT ===")
    
    # Load sentences
    sentences_dict = load_sentences('udhr_major_languages_sentences_extended.json')
    print(f"Loaded {len(sentences_dict)} major world languages.")
    
    # Load model
    model = load_model()
    
    # GlotLID code mapping for major languages
    major_lang_to_glotlid = {
        'english': 'eng',
        'spanish': 'spa',
        'french': 'fra',
        'portuguese': 'por',
        'chinese': 'cmn',
        'hindi': 'hin',
        'bengali': 'ben',
        'german': 'deu',
        'japanese': 'jpn',
        'italian': 'ita',
        'turkish': 'tur',
        'vietnamese': 'vie',
        'korean': 'kor',
        'persian': 'fas',
        'swahili': 'swh',
        'indonesian': 'ind'
    }
    
    # Run classification using the same function as low-resource languages
    results = classify_sentences(model, sentences_dict, major_lang_to_glotlid)
    
    # Analyze results
    language_stats = analyze_results(results)
    
    # Print results
    print_accuracy_table(language_stats, "Major Languages Results")
    
    # Save results
    save_detailed_results(results, language_stats, 'major_languages_results.json')
    
    return results, language_stats

def run_klingon_control_experiment():
    """Run experiment on Klingon control group."""
    print("\n=== KLINGON CONTROL EXPERIMENT ===")
    
    # Load Klingon sentences
    klingon_sentences = []
    with open("klingon.txt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("http"):
                continue
            if '=' in line:
                parts = line.split('=')
                left, right = parts[0].strip(), parts[1].strip()
                if any(x in left for x in ["'", "tlh", "Qapla'", "Hol", "jI", "bI", "Daj", "pu'", "QonoS", "QIt", "yI", "'oH"]):
                    klingon_sentences.append(left)
                elif any(x in right for x in ["'", "tlh", "Qapla'", "Hol", "jI", "bI", "Daj", "pu'", "QonoS", "QIt", "yI", "'oH"]):
                    klingon_sentences.append(right)
            elif any(x in line for x in ["'", "tlh", "Qapla'", "Hol", "jI", "bI", "Daj", "pu'", "QonoS", "QIt", "yI", "'oH"]):
                klingon_sentences.append(line)
    
    print(f"Loaded {len(klingon_sentences)} Klingon sentences.")
    
    # Load model
    model = load_model()
    
    # Classify Klingon sentences
    lang_results = {
        'predictions': [],
        'confidences': [],
        'correct_predictions': 0,
        'klingon_predictions': 0,
        'other_predictions': Counter()
    }
    
    correct_label_variants = generate_script_variants('tlh')
    
    for sentence in klingon_sentences:
        try:
            labels, probabilities = model.predict(sentence, k=1)
            predicted_label = labels[0]
            confidence = probabilities[0]
            
            lang_results['predictions'].append(predicted_label)
            lang_results['confidences'].append(confidence)
            
            if predicted_label in correct_label_variants:
                lang_results['correct_predictions'] += 1
            else:
                lang_results['other_predictions'][predicted_label] += 1
                
        except Exception as e:
            print(f"Error classifying Klingon sentence: {e}")
            continue
    
    results = {'klingon': lang_results}
    language_stats = analyze_results(results)
    
    # Print results
    print_accuracy_table(language_stats, "Klingon Control Results")
    
    # Save results
    save_detailed_results(results, language_stats, 'klingon_results.json')
    
    return results, language_stats

def create_comprehensive_accuracy_table():
    """Create a comprehensive accuracy table combining all experiments."""
    print("\n=== CREATING COMPREHENSIVE ACCURACY TABLE ===")
    
    # Load all results
    try:
        with open('low_resource_results.json', 'r', encoding='utf-8') as f:
            low_resource_data = json.load(f)
        with open('major_languages_results.json', 'r', encoding='utf-8') as f:
            major_languages_data = json.load(f)
        with open('klingon_results.json', 'r', encoding='utf-8') as f:
            klingon_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}. Please run the experiments first.")
        return
    
    # Combine all language stats
    all_stats = {}
    all_stats.update(low_resource_data['language_stats'])
    all_stats.update(major_languages_data['language_stats'])
    all_stats.update(klingon_data['language_stats'])
    
    # Load language names and categories
    language_names = load_language_names()
    language_categories = load_language_categories()
    
    # Create comprehensive table
    print("\n=== COMPREHENSIVE ACCURACY TABLE (ALL LANGUAGES) ===")
    print(f"{'Rank':<4} {'Language':<20} {'Code':<10} {'Category':<12} {'Accuracy':<10} {'Correct/Total':<15}")
    print("-" * 85)
    
    # Sort by accuracy (descending)
    sorted_stats = sorted(all_stats.items(), key=lambda x: x[1]['accuracy'], reverse=True)
    
    for rank, (lang_code, stats) in enumerate(sorted_stats, 1):
        accuracy = stats['accuracy']
        correct = stats['correct_predictions']
        total = stats['total_sentences']
        name = language_names.get(lang_code, lang_code)
        category = language_categories.get(lang_code, 'Unknown')
        
        print(f"{rank:<4} {name:<20} {lang_code:<10} {category:<12} {accuracy:>6.1f}%    {correct:>3}/{total:<3}")
    
    # Summary statistics
    low_resource_stats = [stats for code, stats in all_stats.items() 
                         if language_categories.get(code) == 'Low-resource']
    major_stats = [stats for code, stats in all_stats.items() 
                   if language_categories.get(code) == 'Major']
    
    print(f"\n=== SUMMARY STATISTICS ===")
    print(f"Total languages tested: {len(all_stats)}")
    print(f"Low-resource languages: {len(low_resource_stats)}")
    print(f"Major languages: {len(major_stats)}")
    
    if low_resource_stats:
        low_resource_accuracies = [stats['accuracy'] for stats in low_resource_stats]
        print(f"\nLow-resource languages:")
        print(f"  Average accuracy: {statistics.mean(low_resource_accuracies):.1f}%")
        print(f"  Median accuracy: {statistics.median(low_resource_accuracies):.1f}%")
        print(f"  Min accuracy: {min(low_resource_accuracies):.1f}%")
        print(f"  Max accuracy: {max(low_resource_accuracies):.1f}%")
    
    if major_stats:
        major_accuracies = [stats['accuracy'] for stats in major_stats]
        print(f"\nMajor languages:")
        print(f"  Average accuracy: {statistics.mean(major_accuracies):.1f}%")
        print(f"  Median accuracy: {statistics.median(major_accuracies):.1f}%")
        print(f"  Min accuracy: {min(major_accuracies):.1f}%")
        print(f"  Max accuracy: {max(major_accuracies):.1f}%")
    
    # Save comprehensive results
    comprehensive_data = {
        'all_results': {
            **low_resource_data['results'],
            **major_languages_data['results'],
            **klingon_data['results']
        },
        'all_stats': all_stats,
        'language_names': language_names,
        'language_categories': language_categories,
        'summary': {
            'total_languages': len(all_stats),
            'low_resource_count': len(low_resource_stats),
            'major_count': len(major_stats),
            'low_resource_avg_accuracy': statistics.mean(low_resource_accuracies) if low_resource_stats else 0,
            'major_avg_accuracy': statistics.mean(major_accuracies) if major_stats else 0
        }
    }
    
    with open('comprehensive_results.json', 'w', encoding='utf-8') as f:
        json.dump(comprehensive_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nComprehensive results saved to comprehensive_results.json")

def main():
    """Run the complete language identification experiment."""
    print("=== LANGUAGE IDENTIFICATION EXPERIMENT ===")
    print("Comparing GlotLID performance on low-resource vs major languages")
    print("Focus: Klingon misclassification patterns")
    
    # Run all experiments
    run_low_resource_experiment()
    run_major_languages_experiment()
    run_klingon_control_experiment()
    
    # Create comprehensive table
    create_comprehensive_accuracy_table()
    
    print("\n=== EXPERIMENT COMPLETE ===")

if __name__ == "__main__":
    main() 