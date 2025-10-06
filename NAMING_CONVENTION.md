# NAMING_CONVENTIONS.md

## Purpose
This document defines the naming conventions for all code and file artifacts in this project to ensure consistency, readability, and maintainability across collaborators.

---

## 1. Language

- **Use English only** for all code identifiers: variable names, function names, class names, file names, and folder names.
- Avoid mixing pinyin, abbreviations, or non-English words.
- Example:
  - ✅ `data_path`
  - ❌ `shuju_lujing` (pinyin)
  - ❌ `ds_path` (ambiguous abbreviation)

---

## 2. Variables and Functions

- Use **snake_case** (lowercase words separated by underscores).
- Function names should be verbs or verb phrases, describing what the function does.
- Variable names should be nouns or noun phrases, descriptive and unambiguous.
- Examples:
  - ✅ `load_data()`
  - ✅ `preprocessed_data`
  - ❌ `LoadData()` (camelCase or PascalCase for functions)
  - ❌ `pd` (unless universally recognized like `pd` for pandas)
  - ❌ `tmp1`, `tmp2` (avoid meaningless names)

---

## 3. Classes

- Use **PascalCase** (capitalize the first letter of each word, no underscores).
- Class names should be nouns or noun phrases.
- Examples:
  - ✅ `DataLoader`
  - ✅ `ModelTrainer`
  - ❌ `data_loader`
  - ❌ `modeltrainer`

---

## 4. Constants

- Use **ALL_CAPS_WITH_UNDERSCORES**.
- Examples:
  - ✅ `MAX_EPOCHS = 100`
  - ✅ `DATA_DIR = "/path/to/data"`
  - ❌ `maxEpochs`

---

## 5. Files and Directories

- Use **snake_case** for file and folder names.
- File names should reflect their contents or purpose.
- Examples:
  - ✅ `data_loader.py`
  - ✅ `preprocessing.py`
  - ✅ `tests/`
  - ❌ `DataLoader.py`
  - ❌ `myUtils/`

---

## 6. Abbreviations and Acronyms

- Avoid ambiguous abbreviations.
- Commonly accepted abbreviations may be used if documented.
- Examples:
  - ✅ `config` (configuration)
  - ✅ `num` (number)
  - ❌ `cfg` (unless consistently used project-wide)

---

## 7. Naming Tips

- Be descriptive but concise.
- Avoid single-character names except for counters (`i`, `j`, `k`) in loops.
- Use meaningful prefixes or suffixes when necessary:
  - `_list` for lists (`user_list`)
  - `_dict` for dictionaries (`config_dict`)
  - `_path` for file paths (`output_path`)

---

## 8. Rationale

- Consistency improves readability and reduces cognitive load.
- English-only naming ensures accessibility for international collaborators.
- Clear naming reduces bugs and misunderstanding.

---

## 9. Exceptions

- If external libraries or APIs enforce naming patterns, follow them.
- Temporary variables in small scopes (e.g., list comprehensions) can use short names.

---

Please adhere strictly to these conventions. For any doubts, raise an issue or contact the maintainer.

---

*Last updated: 2025-06-05*

