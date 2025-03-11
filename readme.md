# Instagram Follower Scraper - Installation & Usage Guide

This guide provides step-by-step instructions to install and run the Instagram Follower Scraper in both CLI and GUI modes.

---

## Prerequisites

- **Python 3.8+**: [Download here](https://www.python.org/downloads/)
- **Git** (optional): [Install here](https://git-scm.com/)

---

## Installation

### 1. Create a Virtual Environment (Recommended)

```bash
python -m venv instagram_scraper_env
# Activate the virtual environment
# Linux/Mac:
source instagram_scraper_env/bin/activate
# Windows:
instagram_scraper_env\Scripts\activate
```

### 2. Install Required Libraries

```bash
pip install instaloader pandas tqdm requests cryptography schedule
```

```bash
pip install -r requirements.txt
```


#### Installed Libraries & Their Uses:
- **instaloader**: Instagram API wrapper.
- **pandas**: Data handling and manipulation.
- **tqdm**: CLI progress bar.
- **requests**: Proxy validation.
- **cryptography**: Password encryption.
- **schedule**: Task scheduling.
- **tkinter**: GUI support (pre-installed with Python).


## Another Method is
```bash
# Navigate to directory
cd "/Users/sadmansamee/Documents/Manual Library/tools/instagram_scrapper/"

# Remove old environment
rm -rf instagram_scraper_env

# Use official Python (adjust version to match your download)
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m venv instagram_scraper_env

# Activate
source instagram_scraper_env/bin/activate

# Install dependencies
pip install -r requirements.txt  # Or pip install instaloader pandas tqdm requests cryptography schedule

# Test tkinter
python -c "import tkinter; print('tkinter is available')"

# Run with GUI
python3 instagram_scraper.py --gui
```

## Running the Script

### CLI Mode

#### 1. Basic Usage
```bash
python instagram_scraper.py https://instagram.com/username --new
```

#### 2. With Login
```bash
python instagram_scraper.py https://instagram.com/username --login-user YOUR_USERNAME --login-pass YOUR_PASSWORD --new
```

#### 3. Multi-Account Scraping
```bash
python instagram_scraper.py https://instagram.com/user1 https://instagram.com/user2 --new
```

#### 4. Filters
```bash
python instagram_scraper.py https://instagram.com/username --min-followers 1000 --business-only --verified-only --location "New York" --new
```

#### 5. Scheduled Run
```bash
python instagram_scraper.py https://instagram.com/username --schedule 24 --new
```

---

### GUI Mode

#### 1. Launch GUI
```bash
python instagram_scraper.py --gui
```

#### 2. Steps in GUI:
1. **Input Settings**: Enter Instagram URLs, login credentials, max followers, and optionally load a config file.
2. **Proxy Settings**: Add proxies and set min/max request delays.
3. **Filters**: Set minimum followers, toggle business/non-business/verified, and enter a location filter.
4. **Output Settings**: Choose format (CSV/JSON/SQLite), file path, enable dry run, and select columns.
5. **Start Scraping**: Click "Start" to begin scraping.
   - Use "Pause", "Resume", "Stop", or "Reset" as needed.
   - View live stats, progress, and logs within the window.

#### 3. Example with Pre-filled Values
```bash
python instagram_scraper.py https://instagram.com/username --gui --login-user YOUR_USERNAME --max 100
```

---

## Output Files

- **followers_data.csv / .json** - Scraped data with selected columns.
- **followers.db** - SQLite database (if selected as output format).
- **username_checkpoint.json** - Progress checkpoint.
- **username_cache.json.gz** - Compressed cached follower data.
- **username_scraper.log** - Logs and analytics.

---

## Tips

- **CLI**: Pause execution with `Ctrl + C`; resume with the same command.
- **GUI**: Use control buttons to pause/resume/stop; closing the window stops execution.
- **Logs**: Check logs for detailed analytics, such as follower segments.
- **Configuration Encryption**: Set `SCRAPER_KEY` environment variable for encryption.
  ```bash
  export SCRAPER_KEY="your_key"
  ```
- **Load a Config File in GUI**: Pre-fill settings for easier setup.

---

## Troubleshooting

- **"ModuleNotFoundError"**: Run `pip install` for missing dependencies.
- **GUI Not Showing**: Ensure `tkinter` is available (pre-installed with Python).
- **Proxy Issues**: Verify proxy format (e.g., `http://proxy:port`).

---

🚀 **Happy Scraping!** If you need assistance, refer to script comments or contact the author.