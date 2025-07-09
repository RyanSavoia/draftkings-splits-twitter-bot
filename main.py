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

def get_draftkings_data(endpoint):
    """Fetch data from DraftKings API endpoint"""
    try:
        url = f"{DRAFTKINGS_BASE_URL}/{endpoint}"
        print(f"🌐 Fetching data from {url}")
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Got {data.get('count', 0)} picks from {endpoint}")
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

def format_bet_line(pick):
    """Format a single bet line for tweet"""
    team = pick['team']
    odds = pick['odds']
    market = pick['market_type']
    game_time = pick['game_time']
    
    # Clean up the odds display
    if odds.startswith('−'):
        odds = odds.replace('−', '-')
    
    return f"• {team} {odds} ({market}) - {game_time}"

def create_big_bettor_tweet(data):
    """Create tweet for big bettor alerts"""
    if not data or not data.get('big_bettor_alerts'):
        return None
    
    picks = data['big_bettor_alerts']
    
    lines = []
    lines.append("💰 BIG BETTOR ALERTS 💰")
    lines.append("Big money is flowing heavy on these picks:")
    lines.append("")
    
    for i, pick in enumerate(picks, 1):
        handle_pct = pick['handle_pct']
        bets_pct = pick['bets_pct']
        team = pick['team']
        odds = pick['odds'].replace('−', '-')
        game_time = pick['game_time'].split(', ')[1]  # Get just the time part
        game_title = pick['game_title']
        
        lines.append(f"{i}. {team} {odds} ({game_title})")
        lines.append(f"   💵 {handle_pct} of money | 🎯 {bets_pct} of bets")
        lines.append(f"   ⏰ {game_time}")
        lines.append("")
    
    lines.append("When the money % is way higher than bet %, the big players are backing it.")
    
    return '\n'.join(lines)

def create_square_bets_tweet(data):
    """Create tweet for biggest square bets"""
    if not data or not data.get('biggest_square_bets'):
        return None
    
    picks = data['biggest_square_bets']
    
    lines = []
    lines.append("🤡 BIGGEST SQUARE BETS 🤡")
    lines.append("High public betting % but low money % = fade the public?")
    lines.append("")
    
    for i, pick in enumerate(picks, 1):
        bets_pct = pick['bets_pct']
        handle_pct = pick['handle_pct']
        team = pick['team']
        odds = pick['odds'].replace('−', '-')
        game_time = pick['game_time'].split(', ')[1]  # Get just the time part
        game_title = pick['game_title']
        
        lines.append(f"{i}. {team} {odds} ({game_title})")
        lines.append(f"   📊 {bets_pct} of bets but only {handle_pct} of money")
        lines.append(f"   ⏰ {game_time}")
        lines.append("")
    
    lines.append("The public loves these bets, but the money doesn't. Contrarian play?")
    
    return '\n'.join(lines)

def create_sharp_longshots_tweet(data):
    """Create tweet for sharpest longshots"""
    if not data or not data.get('sharpest_longshots'):
        return None
    
    picks = data['sharpest_longshots']
    
    lines = []
    lines.append("🎯 SHARP LONGSHOTS 🎯")
    lines.append("Big money backing these +200 or higher underdogs:")
    lines.append("")
    
    for i, pick in enumerate(picks, 1):
        handle_pct = pick['handle_pct']
        bets_pct = pick['bets_pct']
        team = pick['team']
        odds = pick['odds'].replace('−', '-')
        game_time = pick['game_time'].split(', ')[1]  # Get just the time part
        game_title = pick['game_title']
        
        lines.append(f"{i}. {team} {odds} ({game_title})")
        lines.append(f"   💎 {handle_pct} of money | 🎯 {bets_pct} of bets")
        lines.append(f"   ⏰ {game_time}")
        lines.append("")
    
    lines.append("When big money backs big underdogs, they know something we don't.")
    
    return '\n'.join(lines)

def create_get_rich_quick_tweet(data):
    """Create tweet for get rich quick picks"""
    if not data or not data.get('get_rich_quick'):
        return None
    
    picks = data['get_rich_quick']
    
    lines = []
    lines.append("🚀 GET RICH QUICK 🚀")
    lines.append("Massive underdogs (+400+) getting serious money:")
    lines.append("")
    
    for i, pick in enumerate(picks, 1):
        handle_pct = pick['handle_pct']
        bets_pct = pick['bets_pct']
        team = pick['team']
        odds = pick['odds'].replace('−', '-')
        game_time = pick['game_time'].split(', ')[1]  # Get just the time part
        game_title = pick['game_title']
        
        lines.append(f"{i}. {team} {odds} ({game_title})")
        lines.append(f"   💰 {handle_pct} of money | 🎯 {bets_pct} of bets")
        lines.append(f"   ⏰ {game_time}")
        lines.append("")
    
    lines.append("These are lottery tickets, but when big money plays them...")
    
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
    
    # Get all DraftKings data
    big_bettor_data = get_draftkings_data("big-bettor-alerts")
    square_bets_data = get_draftkings_data("biggest-square-bets")
    sharp_longshots_data = get_draftkings_data("sharpest-longshots")
    get_rich_quick_data = get_draftkings_data("get-rich-quick")
    
    # Create tweets
    big_bettor_tweet = create_big_bettor_tweet(big_bettor_data)
    square_bets_tweet = create_square_bets_tweet(square_bets_data)
    sharp_longshots_tweet = create_sharp_longshots_tweet(sharp_longshots_data)
    get_rich_quick_tweet = create_get_rich_quick_tweet(get_rich_quick_data)
    
    # Post tweets with delays
    successful_posts = 0
    total_attempts = 0
    
    tweets_to_post = [
        (big_bettor_tweet, "Big Bettor Alerts"),
        (square_bets_tweet, "Square Bets"),
        (sharp_longshots_tweet, "Sharp Longshots"),
        (get_rich_quick_tweet, "Get Rich Quick")
    ]
    
    for tweet_text, tweet_type in tweets_to_post:
        if tweet_text:  # Only count actual tweets
            total_attempts += 1
            
        if post_to_twitter(client, tweet_text, tweet_type):
            if tweet_text:  # Only count successful actual posts
                successful_posts += 1
        
        # Wait between tweets (except after the last one)
        if tweet_text and tweets_to_post.index((tweet_text, tweet_type)) < len(tweets_to_post) - 1:
            print("⏱️ Waiting 60 seconds before next tweet...")
            time.sleep(60)
    
    print(f"\n{'='*50}")
    print(f"✅ Completed: {successful_posts}/{total_attempts} tweets posted")
    print(f"{'='*50}")

if __name__ == "__main__":
    print("🚀 Running DraftKings Splits Bot")
    run_draftkings_tweets()
    print("✅ Completed - exiting")
