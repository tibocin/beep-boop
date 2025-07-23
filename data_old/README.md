# Data Directory Structure

## Overview

This directory contains structured YAML data for the agentic companion's knowledge base, organized for optimal maintainability and RAG processing.

## Current Structure (To Be Refactored)

### Large Files Needing Breakdown:

- `favorites.yaml` (508 lines) → Break into categories
- `enhanced_session1_summary.yaml` (707 lines) → Break into domains
- `features.yaml` (851 lines) → Break by project

## Proposed New Structure

```
data/
├── README.md                           # This file
├── personal/
│   ├── values.yaml                     # Core values and principles
│   ├── personality.yaml                # Personality traits and communication style
│   ├── goals.yaml                      # Personal and professional goals
│   └── interests.yaml                  # Areas of interest and curiosity
├── preferences/
│   ├── movies.yaml                     # Movie preferences and analysis
│   ├── shows.yaml                      # TV show preferences
│   ├── music.yaml                      # Music tastes and genres
│   ├── books.yaml                      # Reading preferences and book lists
│   └── documentaries.yaml              # Documentary preferences
├── career/
│   ├── work_experience.yaml            # Employment history (already good size)
│   ├── technical_skills.yaml           # Programming languages and skills
│   └── projects.yaml                   # Current and past projects
├── projects/
│   ├── beep_boop.yaml                  # Beep-boop project details
│   ├── lumi.yaml                       # Lumi platform features
│   ├── cvpunk.yaml                     # CVPunk/JBhunter features
│   ├── stackr.yaml                     # Stacker DCA features
│   └── revao.yaml                      # Revao features
└── metadata/
    ├── session_meta.yaml               # Session metadata and processing info
    └── tags.yaml                       # Tag definitions and categories
```

## Benefits of This Structure

### 1. **Maintainability**

- Smaller files (50-150 lines each) are easier to edit
- Clear separation of concerns
- Reduced merge conflicts

### 2. **RAG Processing**

- Better chunking granularity
- More precise retrieval
- Improved embedding quality

### 3. **Collaboration**

- Multiple contributors can work on different domains
- Easier code reviews
- Clear ownership areas

### 4. **Testing & Validation**

- Individual file validation
- Easier to test specific domains
- Better error isolation

## Loading Strategy

### Option 1: Lazy Loading

```python
# Load only what's needed
def load_personal_data():
    return {
        'values': load_yaml('data/personal/values.yaml'),
        'personality': load_yaml('data/personal/personality.yaml'),
        'goals': load_yaml('data/personal/goals.yaml')
    }
```

### Option 2: Eager Loading with Caching

```python
# Load all at startup, cache for performance
class DataManager:
    def __init__(self):
        self.cache = {}
        self.load_all_data()

    def load_all_data(self):
        # Load all YAML files into memory
        pass
```

### Option 3: Hybrid Approach

```python
# Load core data eagerly, load preferences on-demand
CORE_DATA = ['personal', 'career', 'projects']
PREFERENCE_DATA = ['preferences']
```

## Migration Plan

1. **Phase 1**: Create new directory structure
2. **Phase 2**: Break down large files into smaller ones
3. **Phase 3**: Update loading mechanisms
4. **Phase 4**: Test RAG processing with new structure
5. **Phase 5**: Remove old files

## File Size Guidelines

- **Target**: 50-150 lines per file
- **Maximum**: 200 lines per file
- **Minimum**: 10 lines per file (for meaningful content)

## Metadata Standards

Each file should include:

```yaml
metadata:
  file_type: "personal|preferences|career|projects|metadata"
  last_updated: "2025-01-22"
  version: "1.0"
  tags: ["relevant", "tags"]
  description: "Brief description of file contents"
```
