# le_slider: Rating Collection Toolbox

A flexible Python framework for collecting continuous ratings of psychoacoustic stimuli from participants. Originally built for Listening Effort (LE) measurement, now generalized to support any continuous rating scale.

**Key Features:**
- 📋 **Configuration-driven** — Define sliders via YAML, no code changes needed
- 🌍 **Multi-language** — Built-in German/English support, extensible to other languages
- 🎚️ **Flexible scales** — Support any continuous rating scale (1-14, 0-100, custom ranges)
- 📊 **FAIR data** — JSON output with complete metadata (frame-level audio sync, timestamps, config)
- 🧪 **Well-tested** — 96 unit tests, 100% passing
- 🔌 **Extensible** — Modular architecture supports custom slider types and audio processing

---

## 📑 Table of Contents

- [Installation](#installation)
  - [Requirements](#requirements)
  - [Step 1: Clone or Download](#step-1-clone-or-download-the-project)
  - [Step 2: Create Virtual Environment](#step-2-create-virtual-environment)
  - [Step 3: Install Dependencies](#step-3-install-dependencies)
- [Quick Start](#quick-start)
  - [Basic Usage](#1-basic-usage-with-default-listening-effort-scale)
  - [Using Configuration Files](#2-using-configuration-files)
  - [Recording Session Workflow](#3-typical-recording-session-workflow)
- [Configuration Guide](#configuration-guide)
  - [Stimulus List Format](#stimulus-list-format)
  - [YAML Format](#configuration-yaml-format)
  - [Example Scales](#example-different-scales)
- [Usage Examples](#usage-examples)
- [Output Data Format](#output-data-format)
- [Troubleshooting](#troubleshooting)
- [File Structure](#file-structure)
- [API Reference](#api-reference)
- [Logging](#logging)
- [For Developers](#for-developers)
- [Citation](#citation)
- [Acknowledgements](#acknowledgements)
- [License](#license)
- [Support & Feedback](#support--feedback)

---

## Installation
This project was used on Windows 11, but I guess it'll run on other systems as well.
[Python 3.11.3](https://www.python.org/downloads/release/python-3113/) was used.

### Step 1: Clone or Download the Project

```bash
cd /path/to/le_slider
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv
```

**Activate virtual environment:**

**Windows (CMD):**
```cmd
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Quick Start

### 1. Default Usage

```bash
python slider_app.py
```

This launches a web browser with the rating interface. By default, the slider will use a subjective Listening Effort scale in a range of 1-14 effort scale categorical units (ESCU) with German category labels. 

### 2. Customizing the Slider

Adapt the config file `config/slider.yaml`. Parameters are explained with comments. Change the parameters as you desire.  
Then, run the app as usual again:
```bash
python slider_app.py
```

### 3. Typical Recording Session Workflow

1. **Program starts** → Settings dialog
2. **Enter settings:**
   - Participant ID (e.g., "VP001")
   - Stimulus list (e.g., `measurement_lists/list_1.txt`)
   - Audio device
3. **Click Submit** → Greetings screen
4. **Click Begin** → Start dialog
5. **Click Start** → Audio plays, user rates with slider
6. **Rating ends** → Post-stimulus dialog (for questionnaire)
7. **Click Continue** → Next stimulus (back to step 5. again or end screen if all done)

---

## Configuration Guide

### Stimulus List Format

Create a `.txt` file with one filename per line (audio files should be in accessible paths):

**Example: `measurement/Measurement_Lists/list_1.txt`**
```
audio/stimulus_1.wav
audio/stimulus_2.wav
audio/stimulus_3.wav
```

### Configuration YAML Format

All slider configurations use this YAML structure:

```yaml
# Required
name: listening_effort          # Unique identifier
min_val: 1                      # Minimum slider value
max_val: 14                     # Maximum slider value
init_val: 7                     # Initial position
step: 0.1                       # Step size between values
marker_step: 1                  # Distance between marker lines

# Optional
categories:                     # Category labels at specific values
  1: "effortless"
  14: "only noise"
language: de                    # Language: 'de' or 'en'
description: "Listening Effort" # Human-readable description
```

### Example: Different Scales

**Speech Quality (1-5 scale):**
```yaml
name: speech_quality
min_val: 1
max_val: 5
init_val: 3
step: 0.1
marker_step: 1
categories:
  1: "very bad"
  3: "fair"
  5: "excellent"
language: en
```

**Noisiness (0-100 scale):**
```yaml
name: noisiness
min_val: 0
max_val: 100
init_val: 50
step: 1
marker_step: 10
language: de
```


### Example 2: Add Speech Quality Measure

```bash
# 1. Copy example config
cp examples/config_speech_quality_en.yaml examples/config_squawk.yaml

# 2. Customize squawk.yaml with your scale

# 3. Update slider_app.py:
DEFAULT_CONFIG_FILE = "examples/config_squawk.yaml"

# 4. Run
python slider_app.py
```


## Output Data Format

Each rating session produces a JSON file with complete metadata:

**File:** `participant_id_stimulus_name.json`

**Structure:**
```json
{
  "version": "1.0",
  "participant_id": "VP001",
  "session_id": "2026-04-02T10:26:00.148950Z",
  "stimulus_file": "stimulus_1.wav",
  "timestamp_start": "2026-04-02T10:26:00.148950Z",
  "timestamp_end": "2026-04-02T10:26:05.123456Z",
  "slider_config": {
    "name": "listening_effort",
    "min_val": 1,
    "max_val": 14,
    "init_val": 7,
    "categories": {
      "1": "effortless",
      "14": "only noise"
    }
  },
  "audio_settings": {
    "sample_rate": 48000,
    "blocksize": 256,
    "buffersize": 4,
    "duration_sec": 5.123
  },
  "recordings": [
    {
      "frame": 0,
      "value": 7.0,
      "raw_value": 7.0,
      "timestamp_rel_sec": 0.0
    },
    {
      "frame": 1,
      "value": 7.5,
      "raw_value": 7.5,
      "timestamp_rel_sec": 0.005
    }
  ]
}
```

**Data Fields:**
- `recordings[].frame` — Sequential frame number (0-based)
- `recordings[].value` — Rating value given at this frame
- `recordings[].timestamp_rel_sec` — Time since audio start (seconds)
- `slider_config` — Complete config used for rating (for FAIR compliance)
- `audio_settings` — Sample rate, blocksize for timing reproduction

### Importing Data into Analysis

**Python (pandas):**
```python
import json
import pandas as pd

with open("VP001_stimulus_1.json", 'r') as f:
    data = json.load(f)

# Extract recordings
df = pd.DataFrame(data['recordings'])
print(df.head())

# Access metadata
participant_id = data['participant_id']
config = data['slider_config']
print(f"Scale: {config['min_val']} - {config['max_val']}")
```

**MATLAB:**
```matlab
data = jsondecode(fileread('VP001_stimulus_1.json'));
ratings = [data.recordings.value];
timestamps = [data.recordings.timestamp_rel_sec];
plot(timestamps, ratings)
```

---