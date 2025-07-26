import tweepy
import json
import requests
from datetime import datetime
import os
import time

# Twitter API credentials from environment variables
TWITTER_API_KEY = os.getenv('API_KEY')
TWITTER_API_SECRET = os.getenv('API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('ACCESS_SECRET')

# DraftKings API endpoints
DRAFTKINGS_BASE_URL = "https://draftkings-splits-scraper-webservice.onrender.com"

def setup_twitter_api():
    """Setup Twitter API v2 client"""
    try:
        print("🐦 Setting up Twitter API...")
        
        required_keys = ['API_KEY', 'API_SECRET', 'ACCESS_TOKEN', 'ACCESS_SECRET']
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        
        if missing_keys:
            print(f"❌ Missing environment variables: {missing_keys}")
            return None
        
        print("🔑 All API keys found")
        
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        
        print("✅ Twitter API client created successfully")
        return client
    except Exception as e:
        print(f"❌ Error setting up Twitter API: {e}")
        return None

def get_sport_data(endpoint):
    """Fetch data from DraftKings API endpoint for specific sport"""
    try:
        url = f"{DRAFTKINGS_BASE_URL}/{endpoint}"
        print(f"🌐 Fetching data from {url}")
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Determine the correct key based on the endpoint
        sport_key_map = {
            'big-bettor-alerts-mlb': 'big_bettor_alerts_mlb',
            'big-bettor-alerts-nba': 'big_bettor_alerts_nba', 
            'big-bettor-alerts-nfl': 'big_bettor_alerts_nfl',
            'big-bettor-alerts-nhl': 'big_bettor_alerts_nhl'
        }
        
        alerts_key = sport_key_map.get(endpoint, 'big_bettor_alerts')
        
        # Filter picks based on 30% rule (handle% must be 30% higher than bets%)
        if data and data.get(alerts_key):
            filtered_picks = []
            for pick in data[alerts_key]:
                try:
                    handle_pct = int(pick['handle_pct'].replace('%', ''))
                    bets_pct = int(pick['bets_pct'].replace('%', ''))
                    
                    if handle_pct >= bets_pct + 30:
                        filtered_picks.append(pick)
                except (ValueError, KeyError):
                    continue  # Skip picks with invalid percentage data
            
            # Sort by biggest difference (handle% - bets%)
            filtered_picks.sort(key=lambda x: 
                int(x['handle_pct'].replace('%', '')) - int(x['bets_pct'].replace('%', '')), 
                reverse=True
            )
            
            # Update the data with filtered picks using the standardized key
            data['big_bettor_alerts'] = filtered_picks
        else:
            # If no data found, set empty list
            data['big_bettor_alerts'] = []
        
        pick_count = len(data.get('big_bettor_alerts', []))
        print(f"✅ Got {pick_count} qualifying picks from {endpoint}")
        return data
    except requests.exceptions.Timeout:
        print(f"⏰ Request timed out for {endpoint}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"🌐 Network error for {endpoint}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error fetching {endpoint}: {e}")
        return None

def get_sport_emoji(sport):
    """Get emoji for sport"""
    emojis = {
        'MLB': '⚾',
        'NBA': '🏀',
        'NFL': '🏈',
        'NHL': '🏒'
    }
    return emojis.get(sport, '💰')

def create_big_bettor_tweet(data, sport):
    """Create tweet for big bettor alerts for specific sport"""
    if not data or not data.get('big_bettor_alerts'):
        return None
    
    picks = data['big_bettor_alerts']
    
    if not picks:
        return None
    
    emoji = get_sport_emoji(sport)
    pick_count = len(picks)
    
    lines = []
    
    # Dynamic header based on count - changed from "games" to "bets"
    if pick_count == 1:
        lines.append(f"{emoji} This {sport} bet has big money backing it today")
    else:
        lines.append(f"{emoji} {pick_count} {sport} bets with big money backing them today")
    
    lines.append("")
    
    for pick in picks:
        handle_pct = pick['handle_pct']
        bets_pct = pick['bets_pct']
        team = pick['team']
        odds = pick['odds'].replace('−', '-')
        game_time = pick['game_time'].split(', ')[1]  # Get just the time part
        game_title = pick['game_title']
        
        lines.append(f"{team} {odds} ({game_title})")
        lines.append(f"🎫 {bets_pct} / 💰 {handle_pct}")
        lines.append(f"{game_time}")
        lines.append("")
    
    lines.append("Drop a ❤️ if you guys are tailing!")
    
    return '\n'.join(lines)

def create_square_bets_tweet(data):
    """Create tweet for biggest square bets (keeping original functionality)"""
    if not data or not data.get('biggest_square_bets'):
        return None
    
    picks = data['biggest_square_bets']
    
    if not picks:
        return None
    
    lines = []
    lines.append("🤡 BIGGEST SQUARE BETS 🤡 (fade these)")
    lines.append("Lots of squares but not a lot of dollars, take the opposite of these bets!")
    lines.append("")
    
    for i, pick in enumerate(picks, 1):
        bets_pct = pick['bets_pct']
        handle_pct = pick['handle_pct']
        team = pick['team']
        odds = pick['odds'].replace('−', '-')
        game_time = pick['game_time'].split(', ')[1]  # Get just the time part
        game_title = pick['game_title']
        
        lines.append(f"{i}. {team} {odds} ({game_title})")
        lines.append(f"   {bets_pct} of bets but only {handle_pct} of money")
        lines.append(f"   {game_time}")
        lines.append("")
    
    lines.append("The public loves these bets, but the money doesn't. Contrarian play?")
    
    return '\n'.join(lines)

def post_to_twitter(client, text, tweet_type):
    """Post tweet to Twitter"""
    try:
        if not text:
            print(f"⚠️ No {tweet_type} tweet to post (no qualifying picks)")
            return True  # Don't count as failure
        
        response = client.create_tweet(text=text)
        print(f"✅ Posted {tweet_type}: {response.data['id']}")
        return True
    except Exception as e:
        print(f"❌ Error posting {tweet_type}: {e}")
        return False

def run_draftkings_tweets():
    """Main function to generate and post DraftKings tweets"""
    print(f"\n{'='*50}")
    print(f"Starting DraftKings tweets at {datetime.now()}")
    print(f"{'='*50}")
    
    # Setup Twitter
    client = setup_twitter_api()
    if not client:
        print("❌ Failed to setup Twitter API")
        return
    
    # Sports to check for big bettor alerts
    sports = [
        ('big-bettor-alerts-mlb', 'MLB'),
        ('big-bettor-alerts-nba', 'NBA'),
        ('big-bettor-alerts-nfl', 'NFL'),
        ('big-bettor-alerts-nhl', 'NHL')
    ]
    
    # Collect all tweets to post
    tweets_to_post = []
    
    # Get big bettor alerts for each sport
    for endpoint, sport_name in sports:
        sport_data = get_sport_data(endpoint)
        if sport_data and sport_data.get('big_bettor_alerts'):
            big_bettor_tweet = create_big_bettor_tweet(sport_data, sport_name)
            if big_bettor_tweet:
                tweets_to_post.append((big_bettor_tweet, f"{sport_name} Big Bettor Alerts"))
    
    # Post tweets with delays
    successful_posts = 0
    total_attempts = len(tweets_to_post)
    
    for i, (tweet_text, tweet_type) in enumerate(tweets_to_post):
        if post_to_twitter(client, tweet_text, tweet_type):
            successful_posts += 1
        
        # Wait between tweets (except after the last one)
        if i < len(tweets_to_post) - 1:
            print("⏱️ Waiting 60 seconds before next tweet...")
            time.sleep(60)
    
    print(f"\n{'='*50}")
    print(f"✅ Completed: {successful_posts}/{total_attempts} tweets posted")
    print(f"{'='*50}")

if __name__ == "__main__":
    print("🚀 Running DraftKings Splits Bot")
    run_draftkings_tweets()
    print("✅ Completed - exiting")
