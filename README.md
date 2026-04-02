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

### Requirements
- Python 3.9 or higher
- pip package manager

### Step 1: Clone or Download the Project

```bash
cd /path/to/le_slider
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv
```

**Activate virtual environment:**

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Core dependencies:**
- `sounddevice` — Audio I/O
- `soundfile` — Audio file reading
- `nicegui` — Web UI framework
- `pyyaml` — Configuration files
- `numpy` — Data processing
- `matplotlib` — Visualization

---

## Quick Start

### 1. Basic Usage (with default Listening Effort scale)

```bash
python slider_app.py
```

This launches a web browser with the rating interface using default settings:
- **Scale:** 1-14 (Listening Effort, German categories)
- **Language:** German
- **Output:** `measurement/Results/`

### 2. Using Configuration Files

Create a config file `my_experiment.yaml`:

```yaml
name: listening_effort
min_val: 1
max_val: 14
init_val: 7
step: 0.1
marker_step: 1
categories:
  1: "effortless"
  3: "light effort"
  5: "moderate effort"
  7: "considerable effort"
  9: "strong effort"
  11: "very strong effort"
  13: "maximum effort"
  14: "only noise"
language: en
```

Then set the config in `slider_app.py`:

```python
DEFAULT_CONFIG_FILE = "my_experiment.yaml"
```

Run the app:
```bash
python slider_app.py
```

### 3. Typical Recording Session Workflow

1. **Program starts** → Settings dialog
2. **Enter settings:**
   - Participant ID (e.g., "VP001")
   - Stimulus list (e.g., `measurement/Measurement_Lists/list_1.txt`)
   - Output directory
   - Audio device
   - Language
3. **Click Submit** → Greetings screen
4. **Click Begin** → Start dialog (for first stimulus)
5. **Click Start** → Audio plays, user rates with slider
6. **Rating ends** → Post-stimulus dialog (for questionnaire)
7. **Click Continue** → Next stimulus (or end screen if all done)

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

### Where to Place Config Files

Place your custom YAML files in:
- `examples/` — For reference configurations
- Or any accessible directory and update `DEFAULT_CONFIG_FILE` in `slider_app.py`

Provided examples (in `examples/`):
- `config_listening_effort_de.yaml` — LE scale, German
- `config_listening_effort_en.yaml` — LE scale, English
- `config_speech_quality_en.yaml` — Speech quality, English
- `config_noisiness_en.yaml` — Noisiness, English

---

## Usage Examples

### Example 1: Run LE Study (German)

```bash
# 1. Open slider_app.py, set:
DEFAULT_CONFIG_FILE = "examples/config_listening_effort_de.yaml"
DEFAULT_STIMULUS_LIST = 'measurement/Measurement_Lists/list_1.txt'

# 2. Run
python slider_app.py

# 3. In UI:
# - Enter participant ID: "VP001"
# - Select stimulus list: list_1.txt
# - Choose output directory: measurement/Results
# - Select audio device
# - Click Submit

# 4. Output: measurement/Results/VP001_stimulus_1.json, etc.
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

### Example 3: Programmatic Session Management

```python
from functions.session import SliderSession
from functions.config import load_slider_config_from_yaml

# Load config from YAML
config = load_slider_config_from_yaml("examples/config_listening_effort_en.yaml")

# Create session
session = SliderSession(
    slider_config=config,
    participant_id="VP001",
    stimulus_list_file="measurement/Measurement_Lists/list_1.txt",
    output_dir="measurement/Results",
    device_id=None,  # Auto-detect
    blocksize=256,
    buffersize=4,
    language="en"
)

# Register callbacks (optional)
session.on_playback_started = lambda: print("Playing audio...")
session.on_playback_finished = lambda: print("Recording saved")

# Play first stimulus
session.start_playback(session.get_current_stimulus())

# When done: save and move to next
session.save_current_recording()
session.next_stimulus()
```

---

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

## Troubleshooting

### Issue: "No audio devices found"

**Problem:** SettingsScreen shows "No stereo output devices found"

**Solution:**
1. Check system audio settings (Windows/macOS sound control panel)
2. Ensure at least one stereo output (speakers/headphones) is connected
3. Try `python -c "import sounddevice; print(sounddevice.query_devices())"`

### Issue: Stimulus file not found

**Problem:** Error "Audio file not found: stimulus_1.wav"

**Solution:**
1. Check stimulus list file paths — are they absolute or relative?
2. If relative, ensure you run `python slider_app.py` from the repo root
3. Example: `measurement/Measurement_Lists/list_1.txt` should contain:
   ```
   audio/stimulus_1.wav
   audio/stimulus_2.wav
   ```

### Issue: Config file errors

**Problem:** Error "Failed to parse YAML file" or "SliderConfig validation failed"

**Solution:**
1. Check YAML syntax (indentation, colons, brackets)
2. Verify all required fields: `name`, `min_val`, `max_val`, `init_val`, `step`, `marker_step`
3. Use `python -c "import yaml; yaml.safe_load(open('config.yaml'))"` to validate YAML
4. Example valid config:
   ```yaml
   name: my_scale
   min_val: 1
   max_val: 7
   init_val: 4
   step: 0.5
   marker_step: 1
   ```

### Issue: Data not saved or wrong location

**Problem:** JSON files not appearing in output directory after recording

**Solution:**
1. Check output directory path (default: `measurement/Results`)
2. Ensure directory is writable: `mkdir -p measurement/Results`
3. Check for errors in logs (terminal shows error messages)
4. Default output: `output_dir/participant_id_stimulus_name.json`

### Issue: "Stimulus list not found" or empty list

**Problem:** SettingsScreen shows empty stimulus list or error

**Solution:**
1. Create the stimulus list directory:
   ```bash
   mkdir -p measurement/Measurement_Lists
   ```
2. Create a `.txt` file with audio filenames (one per line):
   ```bash
   echo "audio/test_1.wav
   audio/test_2.wav" > measurement/Measurement_Lists/list_1.txt
   ```
3. Ensure audio files exist at the paths listed

---

## File Structure

```
le_slider/
├── slider_app.py              # Main application (entry point)
├── calibrate.py               # Audio calibration utility
├── requirements.txt           # Python dependencies
│
├── functions/                 # Core modules
│   ├── session.py             # Session management (orchestration)
│   ├── config.py              # Configuration system (YAML parsing)
│   ├── i18n.py                # Localization (German/English)
│   ├── sliders.py             # Slider abstraction & factory
│   ├── data_io.py             # Recording & JSON export
│   ├── data_schema.py          # JSON schema definition
│   ├── audio_player.py        # Event-driven audio base class
│   ├── utils_audio.py         # Audio implementation (sounddevice)
│   ├── utils_gui.py           # UI components (NiceGUI dialogs)
│   ├── utils_plot.py          # Visualization utilities
│   ├── utils_stats.py         # Statistical functions
│   └── utils_dataproc.py      # Data processing utilities
│
├── tools/                     # Utility scripts
│   └── migrate_npz_to_json.py # Convert legacy NPZ to new JSON format
│
├── tests/                     # Unit tests (96 tests, 100% passing)
│   ├── test_config.py
│   ├── test_session.py
│   ├── test_data_io.py
│   ├── test_audio_player.py
│   ├── test_i18n.py
│   ├── test_migration.py
│   └── test_slider_app_phase4.py
│
├── examples/                  # Example configuration files
│   ├── config_listening_effort_de.yaml
│   ├── config_listening_effort_en.yaml
│   ├── config_speech_quality_en.yaml
│   ├── config_noisiness_en.yaml
│   └── session_config_de.yaml
│
├── measurement/              # Data directory (created by app)
│   ├── Measurement_Lists/    # Stimulus list files
│   │   └── list_1.txt
│   └── Results/              # Output JSON recordings
│       ├── VP001_stimulus_1.json
│       ├── VP001_stimulus_2.json
│       └── ...
│
├── demo/                      # Demo applications
│   ├── show_slider_only.py
│   └── make_realtime_profile_video.py
│
└── doc/                       # Documentation
```

---

## API Reference

### Core Classes

#### `SliderSession`
Orchestrates participant workflow (stimulus management, recording, playback).

```python
session = SliderSession(
    slider_config=config,          # SliderConfig instance
    participant_id="VP001",        # Participant ID
    stimulus_list_file="list.txt", # Stimulus list
    output_dir="output/",          # Output directory
    device_id=None,                # Audio device (None=auto)
    blocksize=256,                 # Audio blocksize
    buffersize=4,                  # Buffer size
    language="de"                  # Language code
)

# Methods
session.start_playback(stimulus_file)      # Start audio playback
session.save_current_recording()           # Save to JSON
session.next_stimulus()                    # Move to next
session.stop_playback()                    # Stop audio
session.get_current_stimulus()             # Current stimulus name
session.has_next_stimulus()                # Check if more stimuli
```

#### `SliderConfig`
Configuration for a rating slider.

```python
config = SliderConfig(
    name="listening_effort",
    min_val=1,
    max_val=14,
    init_val=7,
    step=0.1,
    marker_step=1,
    categories_dict={1: "easy", 14: "hard"},
    language="de"
)

config.validate()  # Validate consistency
```

#### `RatingRecorder`
Records rating values during playback.

```python
recorder = RatingRecorder(
    slider_config=config,
    participant_id="VP001",
    stimulus_file="audio.wav"
)

recorder.set_audio_metadata(...)
recorder.add_frame(rating_value)
recorder.save_to_json("output.json")
```

#### `LanguagePack`
Localization support.

```python
i18n = LanguagePack(language="de")
i18n.set_language("en")
text = i18n.get("key.in.dict")  # Get localized string
```

### Utility Functions

```python
# Configuration I/O
config = load_slider_config_from_yaml("config.yaml")
save_slider_config_to_yaml(config, "new_config.yaml")

# Data I/O
migrate_npz_to_json(npz_file, output_json)  # Legacy data migration

# Audio color feedback
from functions.utils_gui import get_color_from_colormap
color_rgb = get_color_from_colormap(value, min_val, max_val)
```

---

## Logging

The application produces logs to help debug issues:

**Enable debug logging** (in `slider_app.py`):

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Log files show:**
- Config loading status
- Session initialization
- Audio device selection
- Stimulus playback start/stop
- Recording save operations
- Errors and exceptions

**Typical logs:**
```
2026-04-02 10:26:00,123 - functions.session - INFO - Initializing session for participant: VP001
2026-04-02 10:26:00,456 - functions.config - INFO - Successfully loaded slider config: listening_effort
2026-04-02 10:26:05,789 - functions.session - INFO - Starting playback: stimulus_1.wav
2026-04-02 10:26:08,012 - functions.data_io - INFO - Saving recording to JSON: output/VP001_stimulus_1.json
```

---

## For Developers

### Adding a New Rating Scale

1. **Create config file** (`examples/config_my_scale.yaml`):
   ```yaml
   name: my_scale
   min_val: 1
   max_val: 10
   init_val: 5
   step: 0.5
   marker_step: 1
   categories:
     1: "Not at all"
     10: "Extremely"
   language: en
   ```

2. **Update `slider_app.py`**:
   ```python
   DEFAULT_CONFIG_FILE = "examples/config_my_scale.yaml"
   ```

3. **Run and test**!

### Adding a New Language

1. **Edit `functions/i18n.py`** — Add translations to `_build_language_strings()`
2. **Example:**
   ```python
   "fr": {
       "dialog.start.ready": "Prêt à commencer?",
       ...
   }
   ```
3. **Update UI** to allow language selection in SettingsScreen

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_config.py -v

# With coverage
python -m pytest tests/ --cov=functions
```

### Code Quality

```bash
# Check for linting issues
python -m pylint functions/*.py

# Type checking
python -m mypy functions/*.py
```

---

## Citation

If you use this toolbox in research, please cite:

```bibtex
@software{le_slider_2026,
  title={le_slider: Rating Collection Toolbox for Psychoacoustics},
  author={User Name},
  year={2026},
  url={https://github.com/user/le_slider}
}
```

---

## Acknowledgements

This project was created with the assistance of **GitHub Copilot** with **Claude Haiku 4.5** as the underlying language model. The development included:
- Architecture design and modular system organization
- Comprehensive test suite (96 unit tests)
- Configuration system and YAML parsing
- Session management and event-driven audio processing
- Multi-language support (German/English)
- Complete documentation and examples

---

## License

[Add your license information here]

---

## Support & Feedback

For issues, questions, or feature requests:
1. Check the **Troubleshooting** section above
2. Review example files in `examples/`
3. Check test files for usage examples in `tests/`
4. Examine log output for error details

---

**Last Updated:** April 2, 2026
**Version:** 1.0 (Phase 4 Complete)
