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

def create_big_bettor_tweet_sanitized(data, sport):
    """Create Big Money Alert version"""
    if not data or not data.get('big_bettor_alerts'):
        return None
    
    picks = data['big_bettor_alerts']
    
    if not picks:
        return None
    
    # Filter picks to only include today's games
    today_str = datetime.now().strftime('%a, %b %d')  # Format: "Thu, Sep 05"
    todays_picks = []
    
    for pick in picks:
        try:
            game_date_str = pick.get('game_time', '').split(', ')[0]  # Get date part
            if game_date_str == today_str:
                todays_picks.append(pick)
        except (ValueError, KeyError, IndexError):
            continue  # Skip picks with invalid date format
    
    if not todays_picks:
        return None
    
    # Limit to top 3-4 picks only
    todays_picks = todays_picks[:4]
    
    lines = []
    
    # Header with sport emoji
    sport_emoji = get_sport_emoji(sport)
    lines.append(f"{sport_emoji} big money is ACTIVE in the {sport} today")
    lines.append("")
    
    for pick in todays_picks:
        try:
            handle_pct = pick['handle_pct']
            bets_pct = pick['bets_pct']
            team = pick['team']
            odds = pick['odds'].replace('−', '-')
            game_time = pick['game_time'].split(', ')[1]
            
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

def get_todays_nfl_games():
    """Fetch today's NFL games"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{INSIDER_BASE_URL}/nfl/games?from={today}&to={today}"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        games = data.get('games', [])
        print(f"✅ Got {len(games)} NFL games for today")
        return games
    except Exception as e:
        print(f"❌ Error fetching NFL games: {e}")
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

def get_referee_stats(game_id):
    """Fetch referee stats for a specific NFL game"""
    try:
        url = f"{INSIDER_BASE_URL}/nfl/games/{game_id}/referee-stats"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching referee stats for {game_id}: {e}")
        return None

def analyze_referee_over_under_edge(ref_stats):
    """Analyze referee stats to find OVER/UNDER edges with 5%+ ROI in 3+ criteria"""
    if not ref_stats or 'over_under' not in ref_stats:
        return None
    
    ou_data = ref_stats['over_under']
    qualifying_criteria = []
    
    # Check all available criteria for 5%+ ROI
    criteria_to_check = [
        ('over_under', 'Overall'),
        ('conference', 'When in-conference'),
        ('over_under_range', 'When total in range'),
    ]
    
    # Check nested over_under stats for home favorite/underdog
    if 'over_under' in ou_data:
        nested_ou = ou_data['over_under']
        if 'home_favorite' in nested_ou:
            home_fav = nested_ou['home_favorite']
            if home_fav.get('roi', 0) >= 5:
                wins = home_fav.get('wins', 0)
                losses = home_fav.get('losses', 0)
                roi = home_fav.get('roi', 0)
                
                # Determine if this favors OVER or UNDER based on the context
                # If ROI is positive for home_favorite, it means UNDER is profitable when home is favored
                qualifying_criteria.append({
                    'description': 'When home favored',
                    'side': 'UNDER',
                    'record': f"{wins}-{losses}",
                    'roi': roi
                })
        
        if 'home_underdog' in nested_ou:
            home_dog = nested_ou['home_underdog']
            if home_dog.get('roi', 0) >= 5:
                wins = home_dog.get('wins', 0)
                losses = home_dog.get('losses', 0)
                roi = home_dog.get('roi', 0)
                
                qualifying_criteria.append({
                    'description': 'When home underdog',
                    'side': 'UNDER',
                    'record': f"{wins}-{losses}",
                    'roi': roi
                })
    
    # Check main over_under stats
    if 'over_under' in ou_data:
        main_ou = ou_data['over_under']
        over_roi = main_ou.get('over_roi', 0)
        under_roi = main_ou.get('under_roi', 0)
        
        if over_roi >= 5:
            over_hits = main_ou.get('over_hits', 0)
            under_hits = main_ou.get('under_hits', 0)
            qualifying_criteria.append({
                'description': 'Overall',
                'side': 'OVER',
                'record': f"{over_hits}-{under_hits}",
                'roi': over_roi
            })
        elif under_roi >= 5:
            over_hits = main_ou.get('over_hits', 0)
            under_hits = main_ou.get('under_hits', 0)
            qualifying_criteria.append({
                'description': 'Overall',
                'side': 'UNDER',
                'record': f"{under_hits}-{over_hits}",
                'roi': under_roi
            })
    
    # Check conference stats
    if 'conference' in ou_data:
        conf = ou_data['conference']
        conf_roi = conf.get('in_conf_net_roi', 0)
        if abs(conf_roi) >= 5:  # Could be negative, indicating OVER edge
            wins = conf.get('in_conf_wins', 0)
            losses = conf.get('in_conf_losses', 0)
            
            side = 'UNDER' if conf_roi > 0 else 'OVER'
            roi_value = abs(conf_roi)
            
            qualifying_criteria.append({
                'description': 'When in-conference',
                'side': side,
                'record': f"{wins}-{losses}" if side == 'UNDER' else f"{losses}-{wins}",
                'roi': roi_value
            })
    
    # Check over_under_range
    if 'over_under_range' in ou_data:
        ou_range = ou_data['over_under_range']
        range_roi = ou_range.get('ou_range_roi', 0)
        if abs(range_roi) >= 5:
            wins = ou_range.get('ou_range_wins', 0)
            losses = ou_range.get('ou_range_losses', 0)
            total_range = ou_range.get('ou_range', 'range')
            
            side = 'UNDER' if range_roi > 0 else 'OVER'
            roi_value = abs(range_roi)
            
            qualifying_criteria.append({
                'description': f'When total {total_range}',
                'side': side,
                'record': f"{wins}-{losses}" if side == 'UNDER' else f"{losses}-{wins}",
                'roi': roi_value
            })
    
    # Need at least 3 criteria with 5%+ ROI
    if len(qualifying_criteria) < 3:
        return None
    
    # Sort by ROI descending
    qualifying_criteria.sort(key=lambda x: x['roi'], reverse=True)
    
    # Determine the dominant side (most criteria should agree)
    side_count = {}
    for criteria in qualifying_criteria:
        side = criteria['side']
        side_count[side] = side_count.get(side, 0) + 1
    
    dominant_side = max(side_count.items(), key=lambda x: x[1])[0]
    
    return {
        'side': dominant_side,
        'criteria': qualifying_criteria[:3],  # Top 3 by ROI
        'total_qualifying': len(qualifying_criteria)
    }

def create_referee_tweet():
    """Create referee report tweet for NFL games"""
    games = get_todays_nfl_games()
    if not games:
        print("⚠️ No NFL games found for today")
        return None
    
    game_edges = []
    
    for game in games:
        try:
            game_id = game['game_id']
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            
            ref_stats = get_referee_stats(game_id)
            if not ref_stats:
                continue
            
            # Get referee name
            referee_name = ref_stats.get('referee_name', 'Unknown Referee')
            
            edge_analysis = analyze_referee_over_under_edge(ref_stats)
            if edge_analysis:
                # Calculate max ROI for sorting
                max_roi = max(criteria['roi'] for criteria in edge_analysis['criteria'])
                
                game_edges.append({
                    'game_id': game_id,
                    'matchup': f"{away_team} @ {home_team}",
                    'referee': referee_name,
                    'side': edge_analysis['side'],
                    'criteria': edge_analysis['criteria'],
                    'max_roi': max_roi
                })
                
        except Exception as e:
            print(f"❌ Error processing referee stats for game {game.get('name', 'Unknown')}: {e}")
            continue
    
    if not game_edges:
        print("⚠️ No NFL games found with significant referee edges")
        return None
    
    # Sort by max ROI and limit to top 5
    game_edges.sort(key=lambda x: x['max_roi'], reverse=True)
    game_edges = game_edges[:5]
    
    lines = []
    
    # Single game vs multiple games logic
    if len(game_edges) == 1:
        game = game_edges[0]
        lines.append(f"🏈 Referee Report: Take this {game['side']}!")
        lines.append("")
        lines.append(f"{game['referee']} ({game['matchup']}):")
        lines.append(game['side'])
        
        for criteria in game['criteria']:
            lines.append(f"{criteria['description']} {criteria['record']}, {criteria['roi']}% ROI")
        
        lines.append("")
        lines.append("Drop a ❤️ if you're tailing!")
        
    else:
        lines.append("🏈 Referee Report: Take these totals!")
        
        for game in game_edges:
            lines.append("")
            lines.append(f"{game['referee']} ({game['matchup']}):")
            lines.append(game['side'])
            
            for criteria in game['criteria']:
                lines.append(f"{criteria['description']} {criteria['record']}, {criteria['roi']}% ROI")
        
        lines.append("")
        lines.append("Drop a ❤️ if you're tailing!")
    
    return '\n'.join(lines)

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
                                    
                                    # Format prop type with capital letters
                                    if prop_type.lower() == "over":
                                        prop_type_formatted = "O"
                                    elif prop_type.lower() == "under":
                                        prop_type_formatted = "U"
                                    else:
                                        prop_type_formatted = prop_type.title()
                                    
                                    prop_description = f"{player_name} {prop_type_formatted} {opening_line} {prop_clean}"
                                    
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
    lines.append("⚾ 70%+ hit rates in the MLB today")
    lines.append("")
    
    for i, prop in enumerate(top_props, 1):
        hit_rate_formatted = f"{prop['hit_rate']:.1f}%"
        lines.append(f"{i}. {prop['description']}")
        lines.append(f"   {hit_rate_formatted} ({prop['record']})")
        lines.append("")
    
    lines.append("Drop a ❤️ if you're taking any of these!")
    
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
            tweet_text = create_big_bettor_tweet_sanitized(sport_data, sport_name)
            tweet_type = f"{sport_name} Big Money Alert"
                
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
    print("🚀 Running DraftKings Splits Bot")
    run_draftkings_tweets()
    print("✅ Completed - exiting")
