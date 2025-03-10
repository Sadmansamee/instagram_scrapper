import instaloader
import pandas as pd
import time
import argparse
import json
import os
import random
from datetime import datetime
import re

class InstagramFollowerScraper:
    def __init__(self, username, output_file="followers_data.csv", checkpoint_file=None, 
                 max_followers=None, delay_min=1, delay_max=3):
        """
        Initialize the scraper with configuration parameters
        
        Args:
            username: Instagram username to scrape followers from
            output_file: Path to save the CSV output
            checkpoint_file: Path to save/load checkpoint data (None for auto-generate)
            max_followers: Maximum number of followers to scrape
            delay_min: Minimum delay between requests in seconds
            delay_max: Maximum delay between requests in seconds
        """
        self.username = username
        self.output_file = output_file
        self.checkpoint_file = checkpoint_file or f"{username}_checkpoint.json"
        self.max_followers = max_followers
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False
        )
        self.followers_data = []
        self.processed_usernames = set()
        self.resume_username = None
        self.session_count = 0
        self.last_checkpoint_time = time.time()
        self.checkpoint_interval = 60  # Save checkpoint every 60 seconds
        self.user_agent_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        # Define the exact column structure required
        self.columns = [
            'email', 'email.1', 'email.2', 'phone', 'phone.1', 'phone.2', 
            'madid', 'fn', 'ln', 'zip', 'ct', 'st', 'country', 
            'dob', 'doby', 'gen', 'age', 'uid', 'value'
        ]
        
    def login(self, username=None, password=None, session_file=None):
        """Login to Instagram with credentials or session file"""
        try:
            if session_file and os.path.exists(session_file):
                self.L.load_session_from_file(username, session_file)
                print(f"Loaded session from {session_file}")
            elif username and password:
                self.L.login(username, password)
                if session_file:
                    self.L.save_session_to_file(session_file)
                print(f"Logged in as {username}")
            else:
                print("Running without authentication (limited data access)")
            
            # Randomize user agent for more stealth
            if hasattr(self.L.context, '_session'):
                current_ua = random.choice(self.user_agent_list)
                self.L.context._session.headers['User-Agent'] = current_ua
                
            return True
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def load_checkpoint(self):
        """Load checkpoint data if exists"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                
                self.followers_data = checkpoint.get('followers_data', [])
                self.processed_usernames = set(checkpoint.get('processed_usernames', []))
                self.resume_username = checkpoint.get('resume_username')
                
                print(f"Loaded checkpoint: {len(self.processed_usernames)} followers processed")
                return True
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
        return False
    
    def save_checkpoint(self, last_username=None, force=False):
        """Save current progress to checkpoint file"""
        # Only save checkpoint if enough time has passed or forced
        current_time = time.time()
        if not force and (current_time - self.last_checkpoint_time < self.checkpoint_interval):
            return
            
        self.last_checkpoint_time = current_time
        
        checkpoint = {
            'followers_data': self.followers_data,
            'processed_usernames': list(self.processed_usernames),
            'resume_username': last_username,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Create a temporary file to avoid corruption if interrupted
            temp_file = f"{self.checkpoint_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(checkpoint, f)
            
            # Replace the old checkpoint file with the new one
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
            os.rename(temp_file, self.checkpoint_file)
            
            print(f"Checkpoint saved: {len(self.processed_usernames)} followers processed")
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
    
    def adaptive_sleep(self):
        """Sleep for a random duration to avoid detection"""
        # Increase sleep time based on session count to avoid bans
        session_factor = min(1 + (self.session_count / 1000), 3)  # Max 3x increase
        sleep_time = random.uniform(self.delay_min, self.delay_max) * session_factor
        
        # Add occasional longer pauses to simulate natural behavior
        if random.random() < 0.05:  # 5% chance of longer pause
            sleep_time *= random.uniform(2, 4)
            
        time.sleep(sleep_time)
        self.session_count += 1
    
    def extract_emails(self, bio, external_url):
        """Extract up to 3 email addresses from biography and external URL"""
        emails = []
        if bio or external_url:
            content = f"{bio} {external_url or ''}"
            
            # Find all possible email patterns
            email_matches = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', content)
            email_text_matches = re.findall(r'(?:email|e-mail|mail|contact)[\s:]+(.+@.+?)(?=$|\s|[^\w\s@.-])', 
                                          content, re.IGNORECASE)
            
            # Combine and clean matches
            all_email_matches = email_matches + email_text_matches
            for match in all_email_matches:
                potential_email = match.strip().rstrip('.').lower()
                if re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', potential_email) and potential_email not in emails:
                    emails.append(potential_email)
                    if len(emails) >= 3:  # Limit to 3 emails
                        break
        
        # Fill in with empty strings if less than 3 emails
        while len(emails) < 3:
            emails.append("")
            
        return emails
    
    def extract_phone_numbers(self, bio, external_url):
        """Extract up to 3 phone numbers from biography and external URL"""
        phones = []
        if bio or external_url:
            content = f"{bio} {external_url or ''}"
            
            # Phone patterns
            phone_matches = re.findall(r'(?:\+\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}', content)
            phone_text_matches = re.findall(r'(?:phone|tel|call|text)[\s:]+([+\d\(\)\s-]{7,})(?=$|\s|[^+\d\(\)\s-])', 
                                          content, re.IGNORECASE)
            
            # Combine and clean matches
            all_phone_matches = phone_matches + phone_text_matches
            for match in all_phone_matches:
                # Clean the phone number
                clean_phone = re.sub(r'[^\d+]', '', match)
                if len(clean_phone) >= 7 and clean_phone not in phones:  # Must be at least 7 digits
                    phones.append(clean_phone)
                    if len(phones) >= 3:  # Limit to 3 phone numbers
                        break
        
        # Fill in with empty strings if less than 3 phone numbers
        while len(phones) < 3:
            phones.append("")
            
        return phones
    
    def estimate_age_gender(self, full_name, bio):
        """Estimate age and gender based on profile information"""
        # Default values
        gender = ""
        age = None
        dob = ""
        doby = None
        
        # Try to extract birth year/age from bio
        if bio:
            # Look for age indicators
            age_matches = re.findall(r'\b(\d{1,2})\s*(?:yo|years? old|\sy\.?o\.?)\b', bio, re.IGNORECASE)
            if age_matches:
                try:
                    age = int(age_matches[0])
                    # Calculate birth year roughly
                    doby = datetime.now().year - age
                except (ValueError, IndexError):
                    pass
            
            # Look for birth year
            birth_year_matches = re.findall(r'(?:born in|b\.?\s*(?:in)?\s*:?\s*)(\d{4})', bio, re.IGNORECASE)
            if birth_year_matches:
                try:
                    year = int(birth_year_matches[0])
                    if 1940 < year < datetime.now().year:
                        doby = year
                        age = datetime.now().year - year
                except (ValueError, IndexError):
                    pass
                    
            # Attempt to guess gender from bio keywords
            male_indicators = ['he', 'him', 'his', 'male', 'man', 'boy', 'father', 'dad', 'brother', 'son']
            female_indicators = ['she', 'her', 'hers', 'female', 'woman', 'girl', 'mother', 'mom', 'sister', 'daughter']
            
            bio_lower = bio.lower()
            male_count = sum(1 for word in male_indicators if f" {word} " in f" {bio_lower} ")
            female_count = sum(1 for word in female_indicators if f" {word} " in f" {bio_lower} ")
            
            if male_count > female_count:
                gender = "M"
            elif female_count > male_count:
                gender = "F"
        
        # If no age/gender found, use defaults
        if age is None:
            age = ""
        if doby is None:
            doby = ""
            
        return gender, age, dob, doby
    
    def extract_location_data(self, bio):
        """Extract location information from biography"""
        location = ""
        city = ""
        state = ""
        country = ""
        zip_code = ""
        
        if bio:
            # Look for 📍 or 📌 emoji often used for location
            location_emoji_match = re.search(r'[📍📌](.*?)(?=$|\n|[^\w\s,.-])', bio)
            if location_emoji_match:
                location = location_emoji_match.group(1).strip()
                
            # Look for "Location:" or "Based in" patterns
            location_text_match = re.search(r'(?:location|based in|from)[\s:]+(.*?)(?=$|\n|[^\w\s,.-])', 
                                          bio, re.IGNORECASE)
            if location_text_match and not location:
                location = location_text_match.group(1).strip()
                
            # Try to split location into components if found
            if location:
                parts = [p.strip() for p in location.split(',')]
                if len(parts) >= 3:
                    city = parts[0]
                    state = parts[1]
                    country = parts[2]
                elif len(parts) == 2:
                    city = parts[0]
                    country = parts[1]
                elif len(parts) == 1:
                    city = parts[0]
            
            # Look for ZIP/postal code
            zip_match = re.search(r'\b([A-Z0-9]{5,10})\b', bio)
            if zip_match:
                potential_zip = zip_match.group(1)
                # Check if it looks like a ZIP code (numeric or alphanumeric for other countries)
                if re.match(r'^[0-9]{5}(?:-[0-9]{4})?$', potential_zip) or re.match(r'^[A-Z][0-9][A-Z]\s*[0-9][A-Z][0-9]$', potential_zip):
                    zip_code = potential_zip
            
        return location, zip_code, city, state, country
    
    def generate_uid(self, username):
        """Generate a simple numeric user ID from the username"""
        # Create a deterministic numeric ID based on username
        uid = 0
        for char in username:
            uid = (uid * 31 + ord(char)) % 1000000000  # Keep it to 9 digits
        return uid
    
    def scrape_followers(self):
        """Main method to scrape followers data"""
        print(f"Starting to scrape followers for {self.username}")
        
        try:
            # Get profile of the account
            profile = instaloader.Profile.from_username(self.L.context, self.username)
            print(f"Found profile: {profile.username} with {profile.followers} followers")
            
            # Check if resuming from previous run
            resuming = self.load_checkpoint()
            if resuming:
                print(f"Resuming from previous session. Already processed {len(self.processed_usernames)} followers.")
            
            # Get follower iterator
            followers_iterator = profile.get_followers()
            count = len(self.processed_usernames)
            resume_found = self.resume_username is None
            
            print("Collecting follower data...")
            for follower in followers_iterator:
                try:
                    # Skip already processed followers if resuming
                    if follower.username in self.processed_usernames:
                        continue
                        
                    # If resuming and haven't found the resume point yet, skip ahead
                    if not resume_found and self.resume_username:
                        if follower.username == self.resume_username:
                            resume_found = True
                        continue
                    
                    # Extract emails (up to 3)
                    emails = self.extract_emails(follower.biography, follower.external_url)
                    
                    # Extract phone numbers (up to 3)
                    phones = self.extract_phone_numbers(follower.biography, follower.external_url)
                    
                    # Extract first and last name
                    name_parts = follower.full_name.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                    
                    # Extract location data
                    location, zip_code, city, state, country = self.extract_location_data(follower.biography)
                    
                    # Estimate age and gender
                    gender, age, dob, doby = self.estimate_age_gender(follower.full_name, follower.biography)
                    
                    # Generate a unique ID
                    uid = self.generate_uid(follower.username)
                    
                    # Calculate a "value" score based on engagement potential
                    # Higher for business accounts, higher followers, posting frequency
                    value = 1.0  # Base value
                    if follower.is_business_account:
                        value += 0.5
                    if follower.followers > 1000:
                        value += min(follower.followers / 10000, 1.0)
                    if follower.mediacount > 0:
                        value += min(follower.mediacount / 100, 0.5)
                    
                    # Mobile Ad ID placeholder (would require device access)
                    madid = ""
                    
                    # Format data according to required format
                    follower_data = {
                        'email': emails[0],
                        'email.1': emails[1],
                        'email.2': emails[2],
                        'phone': phones[0],
                        'phone.1': phones[1],
                        'phone.2': phones[2],
                        'madid': madid,
                        'fn': first_name,
                        'ln': last_name,
                        'zip': zip_code,
                        'ct': city,
                        'st': state,
                        'country': country,
                        'dob': dob,
                        'doby': doby,
                        'gen': gender,
                        'age': age,
                        'uid': uid,
                        'value': round(value, 2)
                    }
                    
                    # Add to results and mark as processed
                    self.followers_data.append(follower_data)
                    self.processed_usernames.add(follower.username)
                    
                    # Progress reporting
                    count += 1
                    if count % 10 == 0:
                        print(f"Processed {count} followers")
                        
                    # Save checkpoint periodically
                    self.save_checkpoint(follower.username)
                    
                    # Check if we've reached the maximum
                    if self.max_followers and count >= self.max_followers:
                        print(f"Reached maximum number of followers: {self.max_followers}")
                        break
                    
                    # Sleep to avoid rate limiting
                    self.adaptive_sleep()
                    
                except instaloader.exceptions.TooManyRequestsException:
                    print("Rate limit hit! Saving checkpoint and pausing for 5 minutes...")
                    self.save_checkpoint(follower.username, force=True)
                    time.sleep(300)  # 5 minute pause
                    
                except Exception as e:
                    print(f"Error processing follower {follower.username}: {e}")
                    continue
            
            # Save final results
            self.save_checkpoint(force=True)
            self.save_results()
            print(f"Successfully completed. Processed {count} followers.")
            
        except instaloader.exceptions.LoginRequiredException:
            print("Error: Login required to access this profile's followers")
            self.save_checkpoint(force=True)
            
        except instaloader.exceptions.ProfileNotExistsException:
            print(f"Error: Profile {self.username} does not exist")
            
        except instaloader.exceptions.ConnectionException as e:
            print(f"Connection error: {e}")
            print("Saving checkpoint and exiting...")
            self.save_checkpoint(force=True)
            
        except KeyboardInterrupt:
            print("\nInterrupted by user. Saving checkpoint...")
            self.save_checkpoint(force=True)
            self.save_results()
            print("You can resume later with the same command.")
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.save_checkpoint(force=True)
            
    def save_results(self):
        """Save collected data to CSV file with exact column structure"""
        if self.followers_data:
            # Convert to DataFrame with exact column structure
            df = pd.DataFrame(self.followers_data)
            
            # Ensure all required columns exist
            for col in self.columns:
                if col not in df.columns:
                    df[col] = ""
            
            # Reorder columns to match required structure
            df = df[self.columns]
            
            # Save to CSV
            df.to_csv(self.output_file, index=False)
            print(f"Saved {len(df)} followers data to {self.output_file}")
            print(f"CSV file matches the required column structure.")

def main():
    parser = argparse.ArgumentParser(description='Scrape follower data from an Instagram account')
    parser.add_argument('username', type=str, help='Instagram username to scrape followers from')
    parser.add_argument('--output', type=str, default='followers_data.csv', help='Output CSV filename')
    parser.add_argument('--checkpoint', type=str, help='Checkpoint file for resuming (default: {username}_checkpoint.json)')
    parser.add_argument('--max', type=int, default=None, help='Maximum number of followers to scrape')
    parser.add_argument('--login-user', type=str, help='Instagram username for login')
    parser.add_argument('--login-pass', type=str, help='Instagram password for login')
    parser.add_argument('--session-file', type=str, help='Session file to use/save for login')
    parser.add_argument('--delay-min', type=float, default=1.5, help='Minimum delay between requests in seconds')
    parser.add_argument('--delay-max', type=float, default=4.0, help='Maximum delay between requests in seconds')
    parser.add_argument('--new', action='store_true', help='Start a new scrape, ignoring existing checkpoint')
    args = parser.parse_args()
    
    # Delete checkpoint if starting new
    if args.new and (args.checkpoint or f"{args.username}_checkpoint.json"):
        checkpoint_file = args.checkpoint or f"{args.username}_checkpoint.json"
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            print(f"Deleted existing checkpoint: {checkpoint_file}")
    
    # Initialize scraper
    scraper = InstagramFollowerScraper(
        username=args.username,
        output_file=args.output,
        checkpoint_file=args.checkpoint,
        max_followers=args.max,
        delay_min=args.delay_min,
        delay_max=args.delay_max
    )
    
    # Login if credentials provided
    if args.login_user or args.session_file:
        scraper.login(args.login_user, args.login_pass, args.session_file)
    
    # Start scraping
    scraper.scrape_followers()

if __name__ == "__main__":
    main()