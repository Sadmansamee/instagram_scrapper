# Instagram Follower Scraper Guide

This guide explains how to set up and use the Instagram Follower Scraper script.

## Installing Dependencies

First, you'll need to install the required Python packages:

```bash
pip install instaloader pandas
```

These are the main dependencies needed by the script:
- `instaloader`: For interacting with Instagram's data
- `pandas`: For data processing and CSV file output

## Running the Script

The script is designed to scrape follower data from an Instagram account. Here are the basic commands to run it:

### Basic Usage

```bash
python script_name.py USERNAME
```

Replace `script_name.py` with the name of the file where you saved the code, and `USERNAME` with the Instagram username whose followers you want to scrape.

### Advanced Usage Options

The script supports several optional parameters:

```bash
python script_name.py USERNAME [OPTIONS]
```


```
python instagram_scraper.py username_to_scrape --login-user your_username --login-pass your_password
```

Usage Examples:

Basic usage:
```
instagram_scraper.py target_username
```

With authentication (recommended for better results):

```
instagram_scraper.py target_username --login-user your_username --login-pass your_password --session-file session.json
```

Resume a previous run:

```
instagram_scraper.py target_username
```

Start fresh, ignoring previous checkpoint:

```
instagram_scraper.py target_username --new
```

Customize rate limiting (for more aggressive or cautious scraping):

```
instagram_scraper.py target_username --delay-min 2.5 --delay-max 6.0
```

Limit the number of followers:

```
instagram_scraper.py target_username --max 500
```

Available options:

- `--output FILENAME`: Specify the output CSV filename (default: followers_data.csv)
- `--checkpoint FILENAME`: Specify a checkpoint file for resuming interrupted scraping
- `--max NUMBER`: Set maximum number of followers to scrape
- `--login-user USERNAME`: Your Instagram username for login (recommended for better results)
- `--login-pass PASSWORD`: Your Instagram password
- `--session-file FILENAME`: Session file to use/save for login
- `--delay-min SECONDS`: Minimum delay between requests (default: 1.5 seconds)
- `--delay-max SECONDS`: Maximum delay between requests (default: 4.0 seconds)
- `--new`: Start a new scrape, ignoring existing checkpoint

### Example Commands

1. **Basic scraping:**
   ```bash
   python instagram_follower_scraper.py target_username
   ```

2. **With login credentials (recommended for better access):**
   ```bash
   python instagram_follower_scraper.py target_username --login-user your_username --login-pass your_password
   ```

3. **Save to a specific output file:**
   ```bash
   python instagram_follower_scraper.py target_username --output my_results.csv
   ```

4. **Limit the number of followers scraped:**
   ```bash
   python instagram_follower_scraper.py target_username --max 500
   ```

5. **Resume a previous scraping session:**
   ```bash
   python instagram_follower_scraper.py target_username --checkpoint target_username_checkpoint.json
   ```

6. **Using a saved session file (more privacy-friendly than entering password):**
   ```bash
   python instagram_follower_scraper.py target_username --login-user your_username --session-file your_session.txt
   ```

## Important Notes

1. **Rate limiting**: The script includes measures to avoid detection, but Instagram has strict rate limits. Using longer delays (`--delay-min` and `--delay-max`) reduces the risk of being rate-limited.

2. **Login recommended**: While the script can work without login, you'll get much better results by logging in with your Instagram credentials.

3. **Checkpoints**: The script automatically creates checkpoints, so you can resume scraping if it's interrupted.

4. **Output format**: The script outputs a CSV file with specific columns designed for potential marketing use, including email, phone, name, location, and demographic data that it attempts to extract from profiles.

5. **Ethical usage**: Make sure to use this script responsibly and in accordance with Instagram's Terms of Service and applicable privacy laws.

## Troubleshooting

- If you encounter a "Too many requests" error, the script will automatically pause and retry.
- If the script stops unexpectedly, you can resume using the checkpoint file.
- Login issues are common if your account has two-factor authentication enabled. Consider using a session file in that case.