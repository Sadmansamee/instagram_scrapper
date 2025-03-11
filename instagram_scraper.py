import instaloader
import pandas as pd
import time
import argparse
import json
import os
import random
import logging
from datetime import datetime
import re
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import requests
import sqlite3
from cryptography.fernet import Fernet
import signal
import sys
import threading
import smtplib
from email.mime.text import MIMEText
import schedule
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class InstagramFollowerScraper:
    def __init__(self, usernames, output_file="followers_data.csv", checkpoint_file=None, 
                 max_followers=None, delay_min=1.5, delay_max=4.0, max_retries=3, proxies=None, 
                 config_file=None, gui=False):
        self.usernames = usernames if isinstance(usernames, list) else [usernames]
        self.output_file = output_file
        self.checkpoint_file = checkpoint_file or f"{self.usernames[0]}_checkpoint.json"
        self.max_followers = max_followers
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.proxies = proxies or []
        self.config_file = config_file
        self.encryption_key = os.getenv('SCRAPER_KEY') or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.load_config()
        self.L = instaloader.Instaloader(
            download_pictures=False, download_videos=False, download_video_thumbnails=False,
            download_geotags=False, download_comments=False, save_metadata=False, compress_json=False,
            rate_controller=lambda ctx: CustomRateController(ctx)
        )
        self.proxy_stats = {p: {'latency': float('inf'), 'uses': 0} for p in self.proxies}
        self.valid_proxies = self.test_proxies()
        self.set_proxy()
        self.followers_data = []
        self.processed_ids = set()
        self.resume_id = None
        self.paused = False
        self.stopped = False
        self.cache_file = f"{self.usernames[0]}_cache.json.gz"
        self.stats = {'processed': 0, 'business': 0, 'verified': 0}
        self.columns = [
            'username', 'account', 'email', 'email.1', 'email.2', 'phone', 'phone.1', 'phone.2', 
            'madid', 'fn', 'ln', 'zip', 'ct', 'st', 'country', 'location', 'is_business',
            'is_verified', 'dob', 'doby', 'gen', 'age', 'uid', 'value', 'followers_count'
        ]
        logging.basicConfig(filename=f'{self.usernames[0]}_scraper.log', level=logging.INFO,
                           format='%(asctime)s - %(levelname)s - %(message)s')
        signal.signal(signal.SIGINT, self.pause_handler)
        self.gui = gui
        if gui:
            self.setup_gui()

    def load_config(self):
        if self.config_file and os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.proxies = config.get('proxies', self.proxies)
            self.login_user = config.get('login_user')
            self.login_pass = self.cipher.decrypt(config.get('login_pass').encode()).decode() if config.get('login_pass') else None
            self.email_config = config.get('email_config', {})
            logging.info(f"Loaded config from {self.config_file}")

    def test_proxies(self):
        if not self.proxies:
            return []
        with ThreadPoolExecutor(max_workers=min(len(self.proxies), 4)) as executor:
            results = list(executor.map(self.test_proxy, self.proxies))
        valid = [p for p, v in zip(self.proxies, results) if v]
        logging.info(f"Valid proxies: {len(valid)}/{len(self.proxies)}")
        return valid

    def test_proxy(self, proxy):
        start = time.time()
        try:
            requests.get("https://www.instagram.com", proxies={"http": proxy, "https": proxy}, timeout=5)
            latency = time.time() - start
            self.proxy_stats[proxy]['latency'] = latency
            self.proxy_stats[proxy]['uses'] = 1
            return True
        except Exception:
            return False

    def set_proxy(self):
        if self.valid_proxies:
            proxy = min(self.valid_proxies, key=lambda p: self.proxy_stats[p]['latency'] / max(self.proxy_stats[p]['uses'], 1))
            self.proxy_stats[proxy]['uses'] += 1
            self.L.context._session.proxies = {"http": proxy, "https": proxy}
            self.L.context._session.timeout = 10
            logging.info(f"Using proxy: {proxy} (latency: {self.proxy_stats[proxy]['latency']:.2f}s)")

class CustomRateController:
    def __init__(self, context):
        self.context = context
        self.last_request = 0
        self.retry_after = 0
    
    def sleep(self, seconds):
        wait = max(seconds, self.retry_after - time.time())
        time.sleep(max(0, wait))
        self.last_request = time.time()

    def wait_before_query(self):
        try:
            response = self.context._session.get('https://www.instagram.com', timeout=10)
            if response.status_code == 429:
                self.retry_after = time.time() + int(response.headers.get('Retry-After', 60))
                logging.warning(f"Rate limit hit. Waiting until {datetime.fromtimestamp(self.retry_after)}")
                self.sleep(self.retry_after - time.time())
            else:
                self.sleep(random.uniform(1.5, 4.0))
                if random.random() < 0.1:
                    self.sleep(random.uniform(30, 60))
        except Exception:
            self.sleep(random.uniform(5, 10))

def login(self, username=None, password=None, session_file=None):
    username = username or getattr(self, 'login_user', None)
    password = password or getattr(self, 'login_pass', None)
    for attempt in range(self.max_retries):
        try:
            if session_file and os.path.exists(session_file):
                self.L.load_session_from_file(username, session_file)
            elif username and password:
                self.L.login(username, password)
                if session_file:
                    self.L.save_session_to_file(session_file)
            logging.info(f"Logged in as {username}")
            return True
        except Exception as e:
            logging.error(f"Login attempt {attempt + 1} failed: {e}")
            time.sleep(random.uniform(5, 10))
    logging.error("Max login retries reached")
    return False

def load_checkpoint(self):
    for _ in range(self.max_retries):
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                self.followers_data = checkpoint.get('followers_data', [])
                self.processed_ids = set(checkpoint.get('processed_ids', []))
                self.resume_id = checkpoint.get('resume_id')
                logging.info(f"Loaded checkpoint: {len(self.processed_ids)} followers processed")
                return True
            return False
        except Exception as e:
            logging.error(f"Checkpoint load error: {e}")
            time.sleep(1)
    logging.error("Failed to load checkpoint after retries")
    return False

def save_checkpoint(self, last_id=None, force=False):
    if force or (time.time() - getattr(self, 'last_checkpoint', 0) > 60):
        checkpoint = {
            'followers_data': self.followers_data,
            'processed_ids': list(self.processed_ids),
            'resume_id': last_id,
            'timestamp': datetime.now().isoformat()
        }
        for _ in range(self.max_retries):
            try:
                with open(self.checkpoint_file + '.tmp', 'w') as f:
                    json.dump(checkpoint, f)
                os.replace(self.checkpoint_file + '.tmp', self.checkpoint_file)
                self.last_checkpoint = time.time()
                logging.info(f"Checkpoint saved: {len(self.processed_ids)} processed")
                return
            except Exception as e:
                logging.error(f"Checkpoint save error: {e}")
                time.sleep(1)
        logging.error("Failed to save checkpoint after retries")

def load_cache(self):
    if os.path.exists(self.cache_file):
        with gzip.open(self.cache_file, 'rt', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(self, cache):
    with gzip.open(self.cache_file, 'wt', encoding='utf-8') as f:
        json.dump(cache, f)

def validate_email(self, email):
    return bool(re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', email))

def validate_phone(self, phone):
    return bool(re.match(r'^\+?\d{7,15}$', phone))

def extract_data(self, follower, account):
    bio_url = f"{follower.biography} {follower.external_url or ''}"
    emails = [e for e in re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', bio_url) if self.validate_email(e)]
    emails = emails[:3] + [""] * (3 - len(emails[:3]))
    
    phones = [re.sub(r'[^\d+]', '', p) for p in re.findall(r'(?:\+\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}', bio_url)]
    phones = [p for p in phones if self.validate_phone(p)] + [""] * (3 - len(phones[:3]))
    
    name_parts = follower.full_name.split()
    fn = name_parts[0] if name_parts else ""
    ln = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
    location_match = re.search(r'[📍📌](.*?)(?=$|\n)', follower.biography)
    location = location_match.group(1).strip() if location_match else bio_url
    parts = location.split(',') if location else []
    ct = parts[0].strip() if parts else ""
    st = parts[1].strip() if len(parts) > 1 else ""
    country = parts[2].strip() if len(parts) > 2 else ""
    zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', follower.biography)
    zip_code = zip_match.group(0) if zip_match else ""
    
    age_match = re.search(r'\b(\d{1,2})\s*(?:yo|years? old)\b', follower.biography, re.I)
    age = age_match.group(1) if age_match else ""
    doby = datetime.now().year - int(age) if age else ""
    gen = "F" if "she" in follower.biography.lower() else "M" if "he" in follower.biography.lower() else ""
    
    uid = hash(follower.username) % 1000000000
    value = 1.0 + (0.5 if follower.is_business_account else 0) + min(follower.followers / 10000, 1.0)
    
    return {
        'username': follower.username, 'account': account, 'email': emails[0], 'email.1': emails[1], 'email.2': emails[2],
        'phone': phones[0], 'phone.1': phones[1], 'phone.2': phones[2], 'madid': "",
        'fn': fn, 'ln': ln, 'zip': zip_code, 'ct': ct, 'st': st, 'country': country,
        'location': location, 'is_business': str(follower.is_business_account),
        'is_verified': str(follower.is_verified), 'dob': "", 'doby': doby, 'gen': gen, 
        'age': age, 'uid': uid, 'value': round(value, 2), 'followers_count': follower.followers
    }

def process_follower(self, follower, account, min_followers, business_only, non_business_only, verified_only, location_filter):
    if min_followers and follower.followers < min_followers:
        return None
    if business_only and not follower.is_business_account:
        return None
    if non_business_only and follower.is_business_account:
        return None
    if verified_only and not follower.is_verified:
        return None
    if location_filter and location_filter.lower() not in follower.biography.lower():
        return None
    cache = self.load_cache()
    if follower.username in cache:
        return cache[follower.username]
    for attempt in range(self.max_retries):
        try:
            data = self.extract_data(follower, account)
            cache[follower.username] = data
            self.save_cache(cache)
            return data
        except Exception as e:
            logging.error(f"Error processing {follower.username}, attempt {attempt + 1}: {e}")
            time.sleep(random.uniform(5, 10))
    logging.error(f"Failed to process {follower.username} after {self.max_retries} attempts")
    return None

def pause_handler(self, signum, frame):
    self.paused = True
    logging.info("Pausing scrape... Saving checkpoint")
    self.save_checkpoint(force=True)
    if self.gui:
        self.update_gui_status("Paused")
    else:
        print("Paused. Resume with the same command or Ctrl+C again to exit.")
    while self.paused and not self.stopped:
        time.sleep(1)

def update_stats(self, data):
    self.stats['processed'] += 1
    if data['is_business'] == 'True':
        self.stats['business'] += 1
    if data['is_verified'] == 'True':
        self.stats['verified'] += 1
    if self.gui:
        self.stats_label.config(text=f"Processed: {self.stats['processed']}, Business: {self.stats['business']}, Verified: {self.stats['verified']}")
    else:
        sys.stdout.write(f"\rLive Stats: Processed={self.stats['processed']}, Business={self.stats['business']}, Verified={self.stats['verified']}")
        sys.stdout.flush()

def get_dynamic_batch_size(self):
    if not self.valid_proxies:
        return 10
    avg_latency = sum(self.proxy_stats[p]['latency'] for p in self.valid_proxies) / len(self.valid_proxies)
    return max(5, min(20, int(10 / (avg_latency + 0.1))))

def scrape_followers(self, min_followers=None, business_only=False, non_business_only=False, 
                     verified_only=False, location_filter=None, dry_run=False):
    if os.path.exists(self.checkpoint_file) and not hasattr(self, 'start_new') and not self.gui:
        choice = input(f"Checkpoint exists. Resume (r), Start new (n), or Edit settings (e)? ").lower()
        if choice == 'e':
            self.edit_settings()
        self.start_new = choice != 'r'
        if self.start_new:
            os.remove(self.checkpoint_file)
            logging.info("Starting fresh - deleted checkpoint")
    resume = self.load_checkpoint() if not getattr(self, 'start_new', False) else False
    
    total_processed = len(self.followers_data) if resume else 0
    for account in self.usernames:
        logging.info(f"Scraping followers for {account}")
        profile = instaloader.Profile.from_username(self.L.context, account)
        followers = profile.get_followers()
        follower_list = list(followers)
        total = min(self.max_followers or len(follower_list), len(follower_list)) if not resume else total_processed
        
        batch_size = self.get_dynamic_batch_size()
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as executor:
            if self.gui:
                self.progress['maximum'] = total
                self.update_gui_status("Scraping")
            with tqdm(total=total, desc=f"Scraping {account}", unit="follower", disable=self.gui) as pbar:
                for i in range(0, total, batch_size):
                    if self.paused or self.stopped:
                        return
                    batch = follower_list[i:i + batch_size]
                    results = list(executor.map(lambda f: self.process_follower(f, account, min_followers, business_only, non_business_only, verified_only, location_filter), batch))
                    
                    for follower, data in zip(batch, results):
                        if data and follower.userid not in self.processed_ids:
                            if self.resume_id and follower.userid != self.resume_id:
                                continue
                            self.resume_id = None
                            self.followers_data.append(data)
                            self.processed_ids.add(follower.userid)
                            self.update_stats(data)
                            total_processed += 1
                            if self.gui:
                                self.progress['value'] = total_processed
                                self.root.update_idletasks()
                            else:
                                pbar.update(1)
                    
                    if len(self.followers_data) % 10 == 0:
                        logging.info(f"Processed {len(self.followers_data)} followers")
                        self.save_checkpoint(batch[-1].userid if batch else None)
                    
                    if self.max_followers and total_processed >= self.max_followers:
                        break
                    
                    self.set_proxy()
                    self.L.context.rate_controller.wait_before_query()
    
    if not dry_run:
        self.save_checkpoint(force=True)
        self.save_results()
        self.generate_analytics()
        self.send_notification()
        if self.gui:
            self.update_gui_status("Completed")
    else:
        logging.info(f"Dry run complete. Processed {len(self.followers_data)} followers without saving.")
        if self.gui:
            self.update_gui_status("Dry Run Completed")

def edit_settings(self):
    if not self.gui:
        print(f"Current settings: max_followers={self.max_followers}, proxies={self.proxies}")
        self.max_followers = int(input("Max followers (enter to keep): ") or self.max_followers)
        self.min_followers = int(input("Min followers (enter to keep): ") or getattr(self, 'min_followers', 0))
        self.business_only = input("Business only (y/n, enter to keep): ").lower() == 'y' or getattr(self, 'business_only', False)
        self.verified_only = input("Verified only (y/n, enter to keep): ").lower() == 'y' or getattr(self, 'verified_only', False)
        self.location_filter = input("Location filter (enter to keep): ") or getattr(self, 'location_filter', None)

def save_results(self, format="csv", columns=None, db_file=None):
    if not self.followers_data:
        return
    df = pd.DataFrame(self.followers_data, columns=self.columns)
    if columns:
        df = df[columns]
    if format == "csv":
        df.to_csv(self.output_file, index=False)
    elif format == "json":
        df.to_json(self.output_file.replace(".csv", ".json"), orient="records")
    elif format == "sqlite" and db_file:
        conn = sqlite3.connect(db_file)
        df.to_sql('followers', conn, if_exists='replace', index=False)
        conn.close()
    logging.info(f"Saved {len(df)} followers to {self.output_file if format != 'sqlite' else db_file} in {format} format")

def generate_analytics(self):
    if not self.followers_data:
        logging.info("No data for analytics")
        return
    df = pd.DataFrame(self.followers_data)
    total = len(df)
    business_pct = (df['is_business'] == 'True').mean() * 100
    verified_pct = (df['is_verified'] == 'True').mean() * 100
    avg_followers = df['followers_count'].mean()
    success_rate = (total / (total + len(self.processed_ids) - total)) * 100 if total > 0 else 0
    segments = {
        '<100': len(df[df['followers_count'] < 100]),
        '100-1000': len(df[(df['followers_count'] >= 100) & (df['followers_count'] < 1000)]),
        '1000+': len(df[df['followers_count'] >= 1000])
    }
    analytics_text = (f"Analytics: Total={total}, Business={business_pct:.2f}%, Verified={verified_pct:.2f}%, "
                      f"Avg Followers={avg_followers:.0f}, Success Rate={success_rate:.2f}%\nFollower Segments: {segments}")
    logging.info(analytics_text)
    if self.gui:
        self.log_text.insert(tk.END, analytics_text + "\n")
        self.log_text.see(tk.END)

def send_notification(self):
    if not self.email_config:
        return
    msg = MIMEText(f"Scraping complete for {self.usernames}. Processed: {len(self.followers_data)} followers.")
    msg['Subject'] = 'Instagram Scraper Completed'
    msg['From'] = self.email_config['sender']
    msg['To'] = self.email_config['receiver']
    with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
        server.starttls()
        server.login(self.email_config['sender'], self.email_config['smtp_password'])
        server.send_message(msg)
    logging.info("Sent completion email")

def setup_gui(self):
    self.root = tk.Tk()
    self.root.title("Instagram Follower Scraper")
    self.root.geometry("800x900")

    # Main Frame
    main_frame = ttk.Frame(self.root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Input Frame
    input_frame = ttk.LabelFrame(main_frame, text="Input Settings", padding="5")
    input_frame.pack(fill=tk.X, pady=5)

    ttk.Label(input_frame, text="Instagram URLs (comma-separated):").grid(row=0, column=0, sticky="w")
    self.urls_entry = ttk.Entry(input_frame, width=50)
    self.urls_entry.grid(row=0, column=1, padx=5)
    self.urls_entry.insert(0, ",".join(self.usernames))

    ttk.Label(input_frame, text="Login Username:").grid(row=1, column=0, sticky="w")
    self.login_user_entry = ttk.Entry(input_frame, width=50)
    self.login_user_entry.grid(row=1, column=1, padx=5)
    self.login_user_entry.insert(0, self.login_user or "")

    ttk.Label(input_frame, text="Login Password:").grid(row=2, column=0, sticky="w")
    self.login_pass_entry = ttk.Entry(input_frame, width=50, show="*")
    self.login_pass_entry.grid(row=2, column=1, padx=5)
    self.login_pass_entry.insert(0, self.login_pass or "")

    ttk.Label(input_frame, text="Max Followers:").grid(row=3, column=0, sticky="w")
    self.max_followers_entry = ttk.Entry(input_frame, width=10)
    self.max_followers_entry.grid(row=3, column=1, sticky="w", padx=5)
    self.max_followers_entry.insert(0, str(self.max_followers or ""))

    ttk.Label(input_frame, text="Config File:").grid(row=4, column=0, sticky="w")
    self.config_entry = ttk.Entry(input_frame, width=40)
    self.config_entry.grid(row=4, column=1, sticky="w", padx=5)
    self.config_entry.insert(0, self.config_file or "")
    ttk.Button(input_frame, text="Browse", command=self.browse_config).grid(row=4, column=2, padx=5)

    # Proxy Frame
    proxy_frame = ttk.LabelFrame(main_frame, text="Proxy Settings", padding="5")
    proxy_frame.pack(fill=tk.X, pady=5)

    ttk.Label(proxy_frame, text="Proxies (comma-separated):").grid(row=0, column=0, sticky="w")
    self.proxies_entry = ttk.Entry(proxy_frame, width=50)
    self.proxies_entry.grid(row=0, column=1, padx=5)
    self.proxies_entry.insert(0, ",".join(self.proxies))

    ttk.Label(proxy_frame, text="Min Delay (s):").grid(row=1, column=0, sticky="w")
    self.delay_min_entry = ttk.Entry(proxy_frame, width=10)
    self.delay_min_entry.grid(row=1, column=1, sticky="w", padx=5)
    self.delay_min_entry.insert(0, str(self.delay_min))

    ttk.Label(proxy_frame, text="Max Delay (s):").grid(row=2, column=0, sticky="w")
    self.delay_max_entry = ttk.Entry(proxy_frame, width=10)
    self.delay_max_entry.grid(row=2, column=1, sticky="w", padx=5)
    self.delay_max_entry.insert(0, str(self.delay_max))

    # Filter Frame
    filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="5")
    filter_frame.pack(fill=tk.X, pady=5)

    ttk.Label(filter_frame, text="Min Followers:").grid(row=0, column=0, sticky="w")
    self.min_followers_entry = ttk.Entry(filter_frame, width=10)
    self.min_followers_entry.grid(row=0, column=1, sticky="w", padx=5)

    self.business_only_var = tk.BooleanVar()
    ttk.Checkbutton(filter_frame, text="Business Only", variable=self.business_only_var).grid(row=1, column=0, sticky="w")

    self.non_business_only_var = tk.BooleanVar()
    ttk.Checkbutton(filter_frame, text="Non-Business Only", variable=self.non_business_only_var).grid(row=1, column=1, sticky="w")

    self.verified_only_var = tk.BooleanVar()
    ttk.Checkbutton(filter_frame, text="Verified Only", variable=self.verified_only_var).grid(row=2, column=0, sticky="w")

    ttk.Label(filter_frame, text="Location Filter:").grid(row=3, column=0, sticky="w")
    self.location_entry = ttk.Entry(filter_frame, width=20)
    self.location_entry.grid(row=3, column=1, sticky="w", padx=5)

    # Output Frame
    output_frame = ttk.LabelFrame(main_frame, text="Output Settings", padding="5")
    output_frame.pack(fill=tk.X, pady=5)

    ttk.Label(output_frame, text="Output Format:").grid(row=0, column=0, sticky="w")
    self.format_var = tk.StringVar(value="csv")
    ttk.OptionMenu(output_frame, self.format_var, "csv", "json", "sqlite").grid(row=0, column=1, sticky="w", padx=5)

    ttk.Label(output_frame, text="Output File:").grid(row=1, column=0, sticky="w")
    self.output_file_entry = ttk.Entry(output_frame, width=40)
    self.output_file_entry.grid(row=1, column=1, sticky="w", padx=5)
    self.output_file_entry.insert(0, self.output_file)
    ttk.Button(output_frame, text="Browse", command=self.browse_output_file).grid(row=1, column=2, padx=5)

    self.dry_run_var = tk.BooleanVar()
    ttk.Checkbutton(output_frame, text="Dry Run", variable=self.dry_run_var).grid(row=2, column=0, sticky="w")

    ttk.Label(output_frame, text="Columns to Include:").grid(row=3, column=0, sticky="w")
    self.columns_listbox = tk.Listbox(output_frame, selectmode="multiple", height=5)
    for col in self.columns:
        self.columns_listbox.insert(tk.END, col)
    self.columns_listbox.grid(row=3, column=1, pady=5)

    # Control Frame
    control_frame = ttk.Frame(main_frame)
    control_frame.pack(pady=5)

    self.start_button = ttk.Button(control_frame, text="Start", command=self.start_scrape)
    self.start_button.pack(side=tk.LEFT, padx=5)

    self.pause_button = ttk.Button(control_frame, text="Pause", command=self.pause_scrape, state=tk.DISABLED)
    self.pause_button.pack(side=tk.LEFT, padx=5)

    self.resume_button = ttk.Button(control_frame, text="Resume", command=self.resume_scrape, state=tk.DISABLED)
    self.resume_button.pack(side=tk.LEFT, padx=5)

    self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_scrape, state=tk.DISABLED)
    self.stop_button.pack(side=tk.LEFT, padx=5)

    ttk.Button(control_frame, text="Reset", command=self.reset_settings).pack(side=tk.LEFT, padx=5)

    # Status Frame
    status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
    status_frame.pack(fill=tk.X, pady=5)

    self.stats_label = ttk.Label(status_frame, text="Processed: 0, Business: 0, Verified: 0")
    self.stats_label.pack()

    self.progress = ttk.Progressbar(status_frame, length=400, mode='determinate')
    self.progress.pack(pady=5)

    self.status_label = ttk.Label(status_frame, text="Ready")
    self.status_label.pack()

    # Log Frame
    log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
    log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    self.log_text = tk.Text(log_frame, height=10, width=90)
    self.log_text.pack(fill=tk.BOTH, expand=True)

    self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    self.root.mainloop()

def browse_config(self):
    file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if file:
        self.config_entry.delete(0, tk.END)
        self.config_entry.insert(0, file)
        self.config_file = file
        self.load_config()
        self.update_gui_from_config()

def browse_output_file(self):
    file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("JSON", "*.json"), ("SQLite", "*.db")])
    if file:
        self.output_file_entry.delete(0, tk.END)
        self.output_file_entry.insert(0, file)

def update_gui_from_config(self):
    self.proxies_entry.delete(0, tk.END)
    self.proxies_entry.insert(0, ",".join(self.proxies))
    self.login_user_entry.delete(0, tk.END)
    self.login_user_entry.insert(0, self.login_user or "")
    self.login_pass_entry.delete(0, tk.END)
    self.login_pass_entry.insert(0, self.login_pass or "")

def start_scrape(self):
    try:
        self.usernames = self.urls_entry.get().split(",")
        self.login_user = self.login_user_entry.get()
        self.login_pass = self.login_pass_entry.get()
        self.max_followers = int(self.max_followers_entry.get() or 0) or None
        self.proxies = self.proxies_entry.get().split(",")
        self.delay_min = float(self.delay_min_entry.get() or 1.5)
        self.delay_max = float(self.delay_max_entry.get() or 4.0)
        self.min_followers = int(self.min_followers_entry.get() or 0) or None
        self.business_only = self.business_only_var.get()
        self.non_business_only = self.non_business_only_var.get()
        self.verified_only = self.verified_only_var.get()
        self.location_filter = self.location_entry.get() or None
        self.output_file = self.output_file_entry.get()
        self.format = self.format_var.get()
        self.dry_run = self.dry_run_var.get()
        self.selected_columns = [self.columns_listbox.get(i) for i in self.columns_listbox.curselection()]

        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        self.thread = threading.Thread(target=self.scrape_followers, args=(self.min_followers, self.business_only, 
                                                                          self.non_business_only, self.verified_only, 
                                                                          self.location_filter, self.dry_run))
        self.thread.start()
    except ValueError as e:
        messagebox.showerror("Invalid Input", f"Error: {e}")

def pause_scrape(self):
    self.paused = True
    self.pause_button.config(state=tk.DISABLED)
    self.resume_button.config(state=tk.NORMAL)

def resume_scrape(self):
    self.paused = False
    self.pause_button.config(state=tk.NORMAL)
    self.resume_button.config(state=tk.DISABLED)

def stop_scrape(self):
    self.stopped = True
    self.paused = False
    self.start_button.config(state=tk.NORMAL)
    self.pause_button.config(state=tk.DISABLED)
    self.resume_button.config(state=tk.DISABLED)
    self.stop_button.config(state=tk.DISABLED)

def reset_settings(self):
    self.urls_entry.delete(0, tk.END)
    self.login_user_entry.delete(0, tk.END)
    self.login_pass_entry.delete(0, tk.END)
    self.max_followers_entry.delete(0, tk.END)
    self.proxies_entry.delete(0, tk.END)
    self.delay_min_entry.delete(0, tk.END)
    self.delay_min_entry.insert(0, "1.5")
    self.delay_max_entry.delete(0, tk.END)
    self.delay_max_entry.insert(0, "4.0")
    self.min_followers_entry.delete(0, tk.END)
    self.business_only_var.set(False)
    self.non_business_only_var.set(False)
    self.verified_only_var.set(False)
    self.location_entry.delete(0, tk.END)
    self.format_var.set("csv")
    self.output_file_entry.delete(0, tk.END)
    self.output_file_entry.insert(0, "followers_data.csv")
    self.dry_run_var.set(False)
    self.columns_listbox.selection_clear(0, tk.END)
    self.config_entry.delete(0, tk.END)

def update_gui_status(self, status):
    self.status_label.config(text=status)
    self.log_text.insert(tk.END, f"{status}\n")
    self.log_text.see(tk.END)

def on_closing(self):
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        self.stopped = True
        self.paused = False
        self.root.destroy()

def main():
    parser = argparse.ArgumentParser(description='Instagram Follower Scraper')
    parser.add_argument('urls', nargs='*', help='Instagram profile URLs')
    parser.add_argument('--login-user', help='Your Instagram username')
    parser.add_argument('--login-pass', help='Your Instagram password')
    parser.add_argument('--max', type=int, help='Max followers to scrape across all accounts')
    parser.add_argument('--new', action='store_true', help='Start new scrape')
    parser.add_argument('--format', choices=['csv', 'json', 'sqlite'], default='csv', help='Output format')
    parser.add_argument('--db-file', help='SQLite database file (required for sqlite format)')
    parser.add_argument('--proxies', nargs='+', help='List of proxy URLs')
    parser.add_argument('--config', help='Path to JSON config file')
    parser.add_argument('--min-followers', type=int, help='Minimum follower count')
    parser.add_argument('--columns', nargs='+', help='Columns to include', choices=[
        'username', 'account', 'email', 'email.1', 'email.2', 'phone', 'phone.1', 'phone.2', 
        'madid', 'fn', 'ln', 'zip', 'ct', 'st', 'country', 'location', 'is_business',
        'is_verified', 'dob', 'doby', 'gen', 'age', 'uid', 'value', 'followers_count'
    ])
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--business-only', action='store_true', help='Scrape only business accounts')
    group.add_argument('--non-business-only', action='store_true', help='Scrape only non-business accounts')
    parser.add_argument('--verified-only', action='store_true', help='Scrape only verified accounts')
    parser.add_argument('--location', help='Filter by location in bio')
    parser.add_argument('--dry-run', action='store_true', help='Preview results without saving')
    parser.add_argument('--schedule', type=int, help='Run every X hours')
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    args = parser.parse_args()
    
    usernames = [url.split('/')[-1].strip('/') for url in args.urls] if args.urls else ["example"]
    scraper = InstagramFollowerScraper(usernames, max_followers=args.max, proxies=args.proxies, 
                                       config_file=args.config, gui=args.gui)
    
    if args.gui:
        return  # GUI mode runs its own loop
    
    if args.new and os.path.exists(scraper.checkpoint_file):
        os.remove(scraper.checkpoint_file)
        logging.info("Starting fresh - deleted checkpoint")
    scraper.start_new = args.new
    
    if args.login_user and args.login_pass:
        scraper.login(args.login_user, args.login_pass)
    
    if args.schedule:
        def job():
            scraper.scrape_followers(min_followers=args.min_followers, business_only=args.business_only, 
                                    non_business_only=args.non_business_only, verified_only=args.verified_only, 
                                    location_filter=args.location, dry_run=args.dry_run)
            scraper.save_results(format=args.format, columns=args.columns, db_file=args.db_file)
        schedule.every(args.schedule).hours.do(job)
        logging.info(f"Scheduled to run every {args.schedule} hours")
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        scraper.scrape_followers(min_followers=args.min_followers, business_only=args.business_only, 
                                non_business_only=args.non_business_only, verified_only=args.verified_only, 
                                location_filter=args.location, dry_run=args.dry_run)
        if not args.dry_run:
            scraper.save_results(format=args.format, columns=args.columns, db_file=args.db_file)

if __name__ == "__main__":
    main()