# When Constructed Languages Outperform Real Ones: GlotLID's Surprising Performance on Low-Resource vs Constructed Languages

## Overview

The GlotLid model is one of the current baselines for low-resource language identification   (LID), being able to identify more than 1,600 languages, many of which are not available in other popular models. However - is it able to identify low-resource languages better than an artificial, made up one? And what does that mean for LID research?

## Research Question

**"Can a language identification model designed for low-resource languages actually perform better on artificial languages than its intended target languages?"**

## Methodology

### Data Sources
- **Low-resource languages**: 37 languages from the Universal Declaration of Human Rights (UDHR) dataset
- **Major languages**: 16 major world languages from the UDHR dataset  
- **Control group**: Klingon sentences from [Kaggle dataset](https://www.kaggle.com/datasets/mpwolke/cusersmarilonedrivedocumentosklingontxt/code)
- **Model**: GlotLID (Global Language Identification) from Hugging Face Hub

### Experimental Design
1. **Low-resource languages experiment**: Test 37 low-resource languages with ~50 sentences each
2. **Major languages experiment**: Test 16 major world languages with ~50 sentences each
3. **Control group**: Test Klingon with 43 sentences
4. **Analysis**: Compare accuracy rates and misclassification patterns

### Language Categories
- **Low-resource languages**: Indigenous languages, minority languages, and languages with limited digital resources
- **Major languages**: Widely spoken languages with extensive digital presence
- **Control**: Klingon (constructed language) to test baseline performance

## Getting Started

### Installation

1. **Clone or download this repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Experiment

To run the complete language identification experiment:

```bash
python language_identification_experiment.py
```

This will:
- Run experiments on 37 low-resource languages
- Run experiments on 16 major world languages  
- Run the Klingon control experiment
- Generate comprehensive accuracy tables and statistics
- Save detailed results to JSON files

### Individual Experiments

You can also run individual experiments by importing the functions:

```python
from language_identification_experiment import (
    run_low_resource_experiment,
    run_major_languages_experiment,
    run_klingon_control_experiment
)

# Run specific experiments
results, stats = run_low_resource_experiment()
```

## Results

### Comprehensive Accuracy Table (All Languages)

| Rank | Language | Code | Category | Accuracy | Correct/Total |
|------|----------|------|----------|----------|---------------|
| 1 | Yucatec Maya | yua | Low-resource | 100.0% | 48/48 |
| 2 | English | english | Major | 100.0% | 50/50 |
| 3 | Portuguese | portuguese | Major | 100.0% | 50/50 |
| 4 | Chinese | chinese | Major | 100.0% | 50/50 |
| 5 | Hindi | hindi | Major | 100.0% | 50/50 |
| 6 | Bengali | bengali | Major | 100.0% | 23/23 |
| 7 | Japanese | japanese | Major | 100.0% | 50/50 |
| 8 | Turkish | turkish | Major | 100.0% | 50/50 |
| 9 | Vietnamese | vietnamese | Major | 100.0% | 46/46 |
| 10 | Korean | korean | Major | 100.0% | 50/50 |
| 11 | Persian | persian | Major | 100.0% | 37/37 |
| 12 | Greenlandic | kal | Low-resource | 98.0% | 49/50 |
| 13 | Nahuatl | nah | Low-resource | 98.0% | 49/50 |
| 14 | Amuesha | ame | Low-resource | 98.0% | 49/50 |
| 15 | Luvale | lue | Low-resource | 98.0% | 49/50 |
| 16 | Achuar | acu | Low-resource | 98.0% | 49/50 |
| 17 | French | french | Major | 98.0% | 49/50 |
| 18 | Italian | italian | Major | 98.0% | 49/50 |
| 19 | Asháninka | cni | Low-resource | 94.0% | 47/50 |
| 20 | Mende | men | Low-resource | 94.0% | 47/50 |
| 21 | Nomatsiguenga | not | Low-resource | 94.0% | 47/50 |
| 22 | Minangkabau | min | Low-resource | 94.0% | 47/50 |
| 23 | Ido | ido | Low-resource | 94.0% | 47/50 |
| 24 | Klingon | klingon | Control | 93.0% | 40/43 |
| 25 | Madurese | mad | Low-resource | 92.0% | 46/50 |
| 26 | Nigerian Pidgin | pcm | Low-resource | 92.0% | 46/50 |
| 27 | Huasteco | hva | Low-resource | 92.0% | 46/50 |
| 28 | Aguaruna | agr | Low-resource | 92.0% | 46/50 |
| 29 | Matsés | mcf | Low-resource | 92.0% | 46/50 |
| 30 | Indonesian | indonesian | Major | 92.0% | 46/50 |
| 31 | Amarakaeri | amr | Low-resource | 88.0% | 44/50 |
| 32 | Makonde | kde | Low-resource | 86.0% | 43/50 |
| 33 | Krio | kri | Low-resource | 86.0% | 43/50 |
| 34 | Kpelewo | kpe | Low-resource | 84.0% | 42/50 |
| 35 | Arabela | arl | Low-resource | 82.0% | 41/50 |
| 36 | Swahili | swahili | Major | 80.0% | 40/50 |
| 37 | Interlingua | ina | Low-resource | 78.0% | 39/50 |
| 38 | Lunda | lun | Low-resource | 76.0% | 38/50 |
| 39 | Spanish | spanish | Major | 76.0% | 38/50 |
| 40 | German | german | Major | 76.0% | 38/50 |
| 41 | Miskito | miq | Low-resource | 74.0% | 37/50 |
| 42 | Huitoto Murui | huu | Low-resource | 68.0% | 34/50 |
| 43 | Amahuaca | amc | Low-resource | 66.0% | 33/50 |
| 44 | K'iche' | quc | Low-resource | 66.0% | 33/50 |
| 45 | Mam | mam | Low-resource | 66.0% | 33/50 |
| 46 | Limba | lia | Low-resource | 64.0% | 32/50 |
| 47 | Mi'kmaq | mic | Low-resource | 60.0% | 30/50 |
| 48 | Kinyamwezi | nym | Low-resource | 56.0% | 28/50 |
| 49 | Mazahua | maz | Low-resource | 52.0% | 26/50 |
| 50 | Mapudungun | arn | Low-resource | 50.0% | 25/50 |
| 51 | Maninka | man | Low-resource | 48.0% | 24/50 |
| 52 | Mixtec | mix | Low-resource | 44.0% | 22/50 |
| 53 | Lamnso | lns | Low-resource | 24.0% | 12/50 |
| 54 | Ngangela | nba | Low-resource | 16.0% | 8/50 |

### Summary Statistics

**Total languages tested**: 54
- **Low-resource languages**: 37
- **Major languages**: 16

**Low-resource languages**:
- Average accuracy: 77.1%
- Median accuracy: 86.0%
- Min accuracy: 16.0% (Ngangela)
- Max accuracy: 100.0% (Yucatec Maya)

**Major languages**:
- Average accuracy: 95.0%
- Median accuracy: 100.0%
- Min accuracy: 76.0% (Spanish, German)
- Max accuracy: 100.0% (most languages)

**Klingon (Control Group)**:
- Accuracy: 93.0% (40/43)

## Key Findings

### 1. Low-Resource Languages Can Perform Exceptionally Well
- **Yucatec Maya achieved 100% accuracy**, matching the performance of many major languages
- Several low-resource languages (Greenlandic, Nahuatl, Amuesha, Luvale, Achuar) achieved 98% accuracy
- This suggests that language identification performance can achieve decent results even with limited data availability

### 2. Major Languages Perform as Expected
- Most major languages achieved 100% accuracy
- Spanish and German had the lowest accuracy among major languages (76.0%)
- Overall average of 95.0% for major languages

### 3. Klingon Misclassification Hypothesis

- **Klingon (a constructed language) outperformed many real human languages** - achieving 93.0% accuracy and ranking 24th out of 54 languages
- **26 low-resource languages performed worse than Klingon**, including Ngangela (16.0%), Lamnso (24.0%), Mixtec (44.0%), Maninka (48.0%), and many others
- **This finding is particularly interesting** because it demonstrates that a constructed language can be easier for the model to identify than many real human languages, suggesting that the model's training data and architecture may be more effective for certain types of linguistic patterns
- No languages were misclassified as Klingon (0% Klingon misclassification rate across all languages), which suggests it's a good baseline for correctly identifying an artificial language that's not mistaken with human ones.

### 4. Performance Variation
- Low-resource languages showed high variability (16.0% to 100.0% accuracy)
- Major languages showed more consistent performance (76.0% to 100.0% accuracy)
- Some low-resource languages (Ngangela, Lamnso) performed poorly, while others excelled

## Technical Details

### Model Used
- **GlotLID**: Global Language Identification model from Hugging Face Hub
- Supports 1,600+ languages with script variants
- Uses fasttext architecture

### Code Corrections Made
- Fixed language code mappings to match actual GlotLID predictions
- Examples: `man` → `msc`, `amc` → `kaq`, `hva` → `hus`, `nah` → `nch`
- These corrections significantly improved accuracy for several languages

### Data Processing
- Extracted sentences from UDHR dataset
- Filtered to 37 low-resource and 16 major languages
- Used Klingon sentences as control group (cleaned of English text)
- Applied consistent classification methodology across all experiments

## Conclusion

The experiment revealed that:
1. **A constructed language (Klingon) outperformed 26 out of 37 low-resource languages** - the very languages GlotLID was designed to support
2. **Some low-resource languages can achieve excellent language identification accuracy** (Yucatec Maya 100%, several at 98%)
3. **Language identification performance varies widely among low-resource languages** - while some achieve excellent results, many struggle with low accuracy rates

The results suggest that **GlotLID, despite being designed for low-resource languages, actually performs better on a constructed language than on many of its intended target languages**. This finding raises important questions about critically low LID performance on some low-resource languages, as well as on how we can better build datasets for languages with limited data availability.

## Files

- `language_identification_experiment.py` - Main experiment script
- `utils.py` - Utility functions for model loading, data processing, and analysis
- `extract_major_language_sentences.py` - Script to extract sentences for major languages
- `language_names.json` - Mapping from language codes to full language names
- `language_categories.json` - Mapping from language codes to categories (Low-resource/Major/Control)
- `udhr_low_resource_sentences.json` - Low-resource language sentences
- `udhr_major_languages_sentences_extended.json` - Major language sentences (extended)
- `low_resource_results.json` - Low-resource experiment results
- `major_languages_results.json` - Major languages experiment results
- `klingon_results.json` - Klingon control experiment results
- `comprehensive_results.json` - Combined results from all experiments
- `klingon.txt` - Klingon sentences (control group, cleaned of English text)
- `requirements.txt` - Python dependencies 