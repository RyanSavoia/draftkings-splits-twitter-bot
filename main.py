# Add these functions to your existing main.py file

# InsideRedge API credentials
INSIDER_API_KEY = "5c2f9307-ea6c-4a9c-8d8b-b09643a60bfd"
INSIDER_BASE_URL = "https://commercial.insideredgeanalytics.com/api"

def get_todays_mlb_games():
    """Fetch today's MLB games"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{INSIDER_BASE_URL}/mlb/games?from={today}&to={today}"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        games = data.get('games', [])
        print(f"✅ Got {len(games)} MLB games for today")
        return games
    except Exception as e:
        print(f"❌ Error fetching MLB games: {e}")
        return []

def get_player_props(game_id):
    """Fetch player props for a specific game"""
    try:
        url = f"{INSIDER_BASE_URL}/mlb/games/{game_id}/player-props"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching props for {game_id}: {e}")
        return None

def create_mlb_prop_hit_rates_tweet():
    """Create tweet for MLB props with 70%+ hit rates"""
    games = get_todays_mlb_games()
    if not games:
        return None
        
    all_props = []
    
    for game in games:
        try:
            game_id = game['game_id']
            props_data = get_player_props(game_id)
            
            if not props_data or not isinstance(props_data, list):
                continue
            
            for prop_category in props_data:
                prop_key = prop_category.get('prop_key', '')
                prop_title = prop_category.get('title', '')
                players = prop_category.get('players', [])
                
                for player in players:
                    try:
                        player_name = player.get('player_name', '')
                        prop_type = player.get('prop_type', '')
                        opening_line = player.get('opening_line', 0)
                        record = player.get('record', {})
                        
                        # Skip UNDER props except for strikeouts and pitcher outs
                        if prop_type == "under" and prop_key not in ["pitcher_strikeouts", "pitcher_outs"]:
                            continue
                        
                        if isinstance(record, dict):
                            hit = record.get('hit', 0)
                            miss = record.get('miss', 0)
                            total = record.get('total', 0)
                            
                            if total >= 20:  # Minimum sample size
                                hit_rate = (hit / total) * 100
                                
                                if hit_rate >= 70:  # 70%+ hit rate threshold
                                    # Clean up prop title
                                    prop_clean = prop_title.replace(' (Over/Under)', '').replace(' (Yes/No)', '').replace('Batter ', '').replace('Pitcher ', '')
                                    
                                    prop_description = f"{player_name} {prop_type.title()} {opening_line} {prop_clean}"
                                    
                                    all_props.append({
                                        'description': prop_description,
                                        'hit_rate': hit_rate,
                                        'record': f"{hit}-{miss}"
                                    })
                                    
                    except (KeyError, TypeError, ZeroDivisionError):
                        continue
                        
        except Exception as e:
            print(f"❌ Error processing game {game.get('name', 'Unknown')}: {e}")
            continue
    
    if not all_props:
        print("⚠️ No MLB props found with 70%+ hit rates")
        return None
    
    # Sort by hit rate and take top 5
    all_props.sort(key=lambda x: x['hit_rate'], reverse=True)
    top_props = all_props[:5]
    
    lines = []
    lines.append("These MLB picks have 70%+ hit rates")
    lines.append("")
    
    for i, prop in enumerate(top_props, 1):
        hit_rate_formatted = f"{prop['hit_rate']:.1f}%"
        lines.append(f"{i}. {prop['description']}")
        lines.append(f"   {hit_rate_formatted} ({prop['record']})")
        lines.append("")
    
    lines.append("Use these for your lays.")
    
    return '\n'.join(lines)

# Then modify your main run_draftkings_tweets() function to include MLB props:

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
            tweet_text = create_big_bettor_tweet_sanitized(sport_data, sport_name)
            tweet_type = f"{sport_name} Big Money Alert"
                
            if tweet_text:
                tweets_to_post.append((tweet_text, tweet_type))
    
    # Add MLB prop hit rates tweet
    mlb_props_tweet = create_mlb_prop_hit_rates_tweet()
    if mlb_props_tweet:
        tweets_to_post.append((mlb_props_tweet, "MLB Prop Hit Rates"))
    
    # Post tweets with delays
    successful_posts = 0
    total_attempts = len(tweets_to_post)
    
    for i, (tweet_text, tweet_type) in enumerate(tweets_to_post):
        print(f"\n--- Attempting to post {tweet_type} ---")
        if post_to_twitter(client, tweet_text, tweet_type):
            successful_posts += 1
        
        # Wait between tweets (except after the last one)
        if i < len(tweets_to_post) - 1:
            print("⏱️ Waiting 60 seconds before next tweet...")
            time.sleep(60)
    
    print(f"\n{'='*50}")
    print(f"✅ Completed: {successful_posts}/{total_attempts} tweets posted")
    print(f"{'='*50}")import tweepy
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

# InsideRedge API
INSIDER_API_KEY = "5c2f9307-ea6c-4a9c-8d8b-b09643a60bfd"
INSIDER_BASE_URL = "https://commercial.insideredgeanalytics.com/api"

def setup_twitter_api():
    """Setup Twitter API v2 client"""
    try:
        print("Setting up Twitter API...")
        
        required_keys = ['API_KEY', 'API_SECRET', 'ACCESS_TOKEN', 'ACCESS_SECRET']
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        
        if missing_keys:
            print(f"Missing environment variables: {missing_keys}")
            return None
        
        print("All API keys found")
        
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        
        print("Twitter API client created successfully")
        return client
    except Exception as e:
        print(f"Error setting up Twitter API: {e}")
        return None

def get_todays_mlb_games():
    """Fetch today's MLB games"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{INSIDER_BASE_URL}/mlb/games?from={today}&to={today}"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        games = data.get('games', [])
        print(f"Got {len(games)} MLB games for today")
        return games
    except Exception as e:
        print(f"Error fetching MLB games: {e}")
        return []

def get_player_props(game_id):
    """Fetch player props for a specific game"""
    try:
        url = f"{INSIDER_BASE_URL}/mlb/games/{game_id}/player-props"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Error fetching props for {game_id}: {e}")
        return None

def create_high_hitrate_props_tweet(games):
    """Create tweet for MLB props with 70%+ hit rates"""
    all_props = []
    
    for game in games:
        try:
            game_id = game['game_id']
            props_data = get_player_props(game_id)
            
            if not props_data or not isinstance(props_data, list):
                continue
            
            # Process each prop category
            for prop_category in props_data:
                prop_key = prop_category.get('prop_key', '')
                prop_title = prop_category.get('title', '')
                players = prop_category.get('players', [])
                
                for player in players:
                    try:
                        player_name = player.get('player_name', '')
                        prop_type = player.get('prop_type', '')
                        opening_line = player.get('opening_line', 0)
                        record = player.get('record', {})
                        
                        # Skip UNDER props except for strikeouts and pitcher outs
                        if prop_type == "under" and prop_key not in ["pitcher_strikeouts", "pitcher_outs"]:
                            continue
                        
                        # Handle case where record might be a string representation
                        if isinstance(record, str):
                            # Skip string records for now, need to parse them
                            continue
                        elif isinstance(record, dict):
                            hit = record.get('hit', 0)
                            miss = record.get('miss', 0)
                            total = record.get('total', 0)
                            
                            if total >= 20:  # Minimum sample size
                                hit_rate = (hit / total) * 100
                                
                                if hit_rate >= 70:  # 70%+ hit rate threshold
                                    # Clean up prop title for readability
                                    if 'Over/Under' in prop_title:
                                        prop_clean = prop_title.replace(' (Over/Under)', '').replace('Batter ', '').replace('Pitcher ', '')
                                    elif 'Yes/No' in prop_title:
                                        prop_clean = prop_title.replace(' (Yes/No)', '').replace('Pitcher ', '')
                                    else:
                                        prop_clean = prop_title
                                    
                                    prop_description = f"{player_name} {prop_type.title()} {opening_line} {prop_clean}"
                                    
                                    all_props.append({
                                        'description': prop_description,
                                        'hit_rate': hit_rate,
                                        'record': f"{hit}-{miss}",
                                        'total_games': total
                                    })
                                    
                    except (KeyError, TypeError, ZeroDivisionError):
                        continue
                        
        except Exception as e:
            print(f"Error processing game {game.get('name', 'Unknown')}: {e}")
            continue
    
    if not all_props:
        print("No props found with 70%+ hit rates")
        return None
    
    # Sort by hit rate (highest first) and take top 5
    all_props.sort(key=lambda x: x['hit_rate'], reverse=True)
    top_props = all_props[:5]
    
    lines = []
    lines.append("These MLB picks have 70%+ hit rates")
    lines.append("")
    
    for i, prop in enumerate(top_props, 1):
        hit_rate_formatted = f"{prop['hit_rate']:.1f}%"
        lines.append(f"{i}. {prop['description']}")
        lines.append(f"   {hit_rate_formatted} ({prop['record']})")
        lines.append("")
    
    lines.append("Historical data speaks.")
    
    return '\n'.join(lines)

def post_to_twitter(client, text, tweet_type):
    """Post tweet to Twitter"""
    try:
        if not text:
            print(f"No {tweet_type} tweet to post (no qualifying data)")
            return True
        
        response = client.create_tweet(text=text)
        print(f"Posted {tweet_type}: {response.data['id']}")
        return True
    except Exception as e:
        print(f"Error posting {tweet_type}: {e}")
        return False

def run_mlb_prop_tweets():
    """Main function to generate and post MLB prop tweets"""
    print(f"Starting MLB prop tweets at {datetime.now()}")
    print("="*50)
    
    # Setup Twitter
    client = setup_twitter_api()
    if not client:
        print("Failed to setup Twitter API")
        return
    
    # Get today's MLB games
    games = get_todays_mlb_games()
    if not games:
        print("No MLB games found for today")
        return
    
    # Generate high hit rate props tweet
    props_tweet = create_high_hitrate_props_tweet(games)
    
    if props_tweet:
        success = post_to_twitter(client, props_tweet, "MLB High Hit Rate Props")
        if success:
            print("Successfully posted MLB props tweet")
        else:
            print("Failed to post MLB props tweet")
    else:
        print("No high hit rate props found to tweet")
    
    print("="*50)
    print("Completed MLB prop tweets")

if __name__ == "__main__":
    print("Running MLB Props Hit Rate Bot")
    run_mlb_prop_tweets()
    print("Completed - exiting")
