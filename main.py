import tweepy
import json
import requests
from datetime import datetime, timedelta
import os
import time

# Twitter API credentials from environment variables
TWITTER_API_KEY = os.getenv('API_KEY')
TWITTER_API_SECRET = os.getenv('API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
TWITTER_ACCESS_TOKEN_SECRET = os.getenv('ACCESS_SECRET')

# InsideRedge API credentials
INSIDER_API_KEY = "5c2f9307-ea6c-4a9c-8d8b-b09643a60bfd"
INSIDER_BASE_URL = "https://commercial.insideredgeanalytics.com/api"

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

def get_insider_games(sport, days_ahead=1):
    """Fetch games from InsideRedge API for specified sport"""
    try:
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)

        from_date = today.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')

        url = f"{INSIDER_BASE_URL}/{sport.lower()}/games?from={from_date}&to={to_date}"
        print(f"🌐 Fetching {sport} games from {url}")
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=30)
        response.raise_for_status()

        data = response.json()
        games = data.get('games', [])
        print(f"✅ Got {len(games)} {sport} games")

        return games
    except Exception as e:
        print(f"❌ Error fetching {sport} games: {e}")
        return []

def convert_insider_to_big_bettor_format(games, sport):
    """Convert InsideRedge game data to big bettor alert format"""
    big_bettor_alerts = []
    
    for game in games:
        try:
            public_money = game.get('public_money_stats', {})
            odds = game.get('odds', {})
            
            # Extract team info
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            game_date = game.get('game_date', '')
            
            # Format game time
            if game_date:
                try:
                    dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                    game_time = dt.strftime('%I:%M %p')
                except:
                    game_time = 'TBD'
            else:
                game_time = 'TBD'

            # Get spread info
            spread = odds.get('spread', 0)
            away_spread_odds = odds.get('away_team_odds', {}).get('spread_odds', -110)
            home_spread_odds = odds.get('home_team_odds', {}).get('spread_odds', -110)

            # Process spread bets for both teams
            spread_away_bets = public_money.get('public_money_spread_away_bets_pct', 0)
            spread_away_stake = public_money.get('public_money_spread_away_stake_pct', 0)
            spread_home_bets = public_money.get('public_money_spread_home_bets_pct', 0)
            spread_home_stake = public_money.get('public_money_spread_home_stake_pct', 0)
            
            # Check away team spread (they get + spread)
            if spread_away_stake >= spread_away_bets + 30:
                away_spread_display = f"+{abs(spread)}" if spread < 0 else f"+{spread}"
                big_bettor_alerts.append({
                    'team': away_team,
                    'odds': f"{away_spread_display} ({away_spread_odds:+d})",
                    'bets_pct': f"{spread_away_bets}%",
                    'handle_pct': f"{spread_away_stake}%",
                    'game_time': game_time
                })
            
            # Check home team spread (they get - spread)
            if spread_home_stake >= spread_home_bets + 30:
                home_spread_display = f"-{abs(spread)}" if spread > 0 else f"{spread}"
                big_bettor_alerts.append({
                    'team': home_team,
                    'odds': f"{home_spread_display} ({home_spread_odds:+d})",
                    'bets_pct': f"{spread_home_bets}%",
                    'handle_pct': f"{spread_home_stake}%",
                    'game_time': game_time
                })
            
            # Also check moneyline bets
            ml_away_bets = public_money.get('public_money_ml_away_bets_pct', 0)
            ml_away_stake = public_money.get('public_money_ml_away_stake_pct', 0)
            ml_home_bets = public_money.get('public_money_ml_home_bets_pct', 0)
            ml_home_stake = public_money.get('public_money_ml_home_stake_pct', 0)
            
            away_ml = odds.get('away_team_odds', {}).get('moneyline', 0)
            home_ml = odds.get('home_team_odds', {}).get('moneyline', 0)
            
            # Check away team moneyline
            if ml_away_stake >= ml_away_bets + 30:
                big_bettor_alerts.append({
                    'team': away_team,
                    'odds': f"ML ({away_ml:+d})",
                    'bets_pct': f"{ml_away_bets}%",
                    'handle_pct': f"{ml_away_stake}%",
                    'game_time': game_time
                })
            
            # Check home team moneyline
            if ml_home_stake >= ml_home_bets + 30:
                big_bettor_alerts.append({
                    'team': home_team,
                    'odds': f"ML ({home_ml:+d})",
                    'bets_pct': f"{ml_home_bets}%",
                    'handle_pct': f"{ml_home_stake}%",
                    'game_time': game_time
                })
                
        except Exception as e:
            print(f"❌ Error processing game: {e}")
            continue
    
    # Sort by biggest difference (handle% - bets%)
    big_bettor_alerts.sort(key=lambda x: 
        int(x['handle_pct'].replace('%', '')) - int(x['bets_pct'].replace('%', '')), 
        reverse=True
    )
    
    return big_bettor_alerts

def get_sport_emoji(sport):
    """Get emoji for sport"""
    emojis = {
        'MLB': '⚾',
        'NBA': '🏀', 
        'NFL': '🏈',
        'NHL': '🏒'
    }
    return emojis.get(sport, '💰')

def create_big_bettor_tweet_sanitized(data, sport):
    """Create tweet text from big bettor data"""
    if not data or not data.get('big_bettor_alerts'):
        return None
    
    picks = data['big_bettor_alerts']
    
    if not picks:
        return None
    
    # Limit to top 3-4 picks only
    picks = picks[:4]
    
    lines = []
    
    # Header with sport emoji
    sport_emoji = get_sport_emoji(sport)
    lines.append(f"{sport_emoji} big money is ACTIVE in {sport} today")
    lines.append("")
    
    for pick in picks:
        try:
            handle_pct = pick['handle_pct']
            bets_pct = pick['bets_pct']
            team = pick['team']
            odds = pick['odds'].replace('−', '-')
            game_time = pick['game_time']

            lines.append(f"{team} {odds}")
            lines.append(f"🎫 {bets_pct} / 💰 {handle_pct}")
            lines.append(f"{game_time}")
            lines.append("")
            
        except (ValueError, KeyError):
            continue
    
    lines.append("Drop a ❤️ if you're taking any of these!")
    
    return '\n'.join(lines)

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
                                    
                                    # Format prop description
                                    if prop_type.lower() == "over":
                                        if opening_line == 0.5:
                                            prop_description = f"{player_name} 1+ {prop_clean}"
                                        else:
                                            target_number = int(opening_line + 0.5) if opening_line % 1 == 0.5 else int(opening_line + 1)
                                            prop_description = f"{player_name} {target_number}+ {prop_clean}"
                                    elif prop_type.lower() == "under":
                                        target_number = int(opening_line)
                                        prop_description = f"{player_name} less than {target_number} {prop_clean}"
                                    else:
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
    lines.append("these MLB players will make you 💰 today")
    lines.append("")
    
    for i, prop in enumerate(top_props, 1):
        hit_rate_formatted = f"{prop['hit_rate']:.1f}%"
        lines.append(f"{i}. {prop['description']}")
        lines.append(f"   {hit_rate_formatted} ({prop['record']} this season)")
        lines.append("")
    
    lines.append("Drop a ❤️ if you're taking any of these!")
    
    return '\n'.join(lines)

def post_to_twitter(client, text, tweet_type):
    """Post tweet to Twitter with better error handling"""
    try:
        if not text:
            print(f"⚠️ No {tweet_type} tweet to post (no qualifying picks)")
            return True  # Don't count as failure
        
        # Check if client has proper permissions by trying to get own user info first
        try:
            me = client.get_me()
            print(f"✅ Authenticated as: {me.data.username}")
        except Exception as auth_error:
            print(f"❌ Authentication issue: {auth_error}")
            print("💡 Check your Twitter API permissions - you might need 'Read and Write' access")
            return False
        
        response = client.create_tweet(text=text)
        print(f"✅ Posted {tweet_type}: {response.data['id']}")
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if '403' in error_msg or 'forbidden' in error_msg:
            print(f"❌ Permission denied for {tweet_type}")
            print("💡 Your Twitter app needs 'Read and Write' permissions")
            print("💡 Go to Twitter Developer Portal > Your App > Settings > User authentication settings")
        elif 'duplicate' in error_msg:
            print(f"⚠️ Duplicate tweet detected for {tweet_type}")
        else:
            print(f"❌ Error posting {tweet_type}: {e}")
        return False

def run_big_bettor_tweets():
    """Main function to generate and post big bettor tweets"""
    print(f"\n{'='*50}")
    print(f"Starting Big Bettor tweets at {datetime.now()}")
    print(f"{'='*50}")

    # Setup Twitter
    client = setup_twitter_api()
    if not client:
        print("❌ Failed to setup Twitter API")
        return

    # Sports available from InsideRedge API  
    sports = [
        ('MLB', 'MLB'),
        ('NFL', 'NFL')
    ]

    # Collect all tweets to post
    tweets_to_post = []

    # Get big bettor alerts for each sport from InsideRedge
    for sport_name, display_name in sports:
        games = get_insider_games(sport_name)
        if games:
            big_bettor_alerts = convert_insider_to_big_bettor_format(games, sport_name)
            if big_bettor_alerts:
                # Create data structure compatible with existing tweet function
                sport_data = {'big_bettor_alerts': big_bettor_alerts}
                tweet_text = create_big_bettor_tweet_sanitized(sport_data, display_name)
                tweet_type = f"{display_name} Big Money Alert"
                    
                if tweet_text:
                    tweets_to_post.append((tweet_text, tweet_type))

    # Add MLB prop hit rates tweet
    mlb_props_tweet = create_mlb_prop_hit_rates_tweet()
    if mlb_props_tweet:
        tweets_to_post.append((mlb_props_tweet, "MLB Prop Hit Rates"))

    # Add NFL referee report tweet
    nfl_referee_tweet = create_referee_tweet()
    if nfl_referee_tweet:
        tweets_to_post.append((nfl_referee_tweet, "NFL Referee Report"))

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
    print(f"{'='*50}")

if __name__ == "__main__":
    print("🚀 Running Big Bettor Alerts Bot")
    run_big_bettor_tweets()
    print("✅ Completed - exiting")
