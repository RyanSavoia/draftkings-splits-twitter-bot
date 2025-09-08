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
    if not ref_stats or 'referee_odds' not in ref_stats or 'over_under' not in ref_stats['referee_odds']:
        return None
    
    ou_data = ref_stats['referee_odds']['over_under']
    qualifying_criteria = []
    
    # Get main sections
    main_ou = ou_data.get('over_under', {})
    conf = ou_data.get('conference', {})
    range_data = ou_data.get('over_under_range', {})
    
    # Check overall UNDER ROI
    under_roi = main_ou.get('under_roi', 0)
    if under_roi >= 5:
        under_hits = main_ou.get('under_hits', 0)
        over_hits = main_ou.get('over_hits', 0)
        qualifying_criteria.append({
            'description': 'Overall',
            'side': 'UNDER',
            'record': f"{under_hits}-{over_hits}",
            'roi': round(under_roi, 1)
        })
    
    # Check overall OVER ROI
    over_roi = main_ou.get('over_roi', 0)
    if abs(over_roi) >= 5 and over_roi > 0:
        over_hits = main_ou.get('over_hits', 0)
        under_hits = main_ou.get('under_hits', 0)
        qualifying_criteria.append({
            'description': 'Overall',
            'side': 'OVER',
            'record': f"{over_hits}-{under_hits}",
            'roi': round(abs(over_roi), 1)
        })
    
    # Check home favorite
    if 'home_favorite' in main_ou:
        home_fav = main_ou['home_favorite']
        hf_roi = home_fav.get('roi', 0)
        if abs(hf_roi) >= 5:
            wins = home_fav.get('wins', 0)
            losses = home_fav.get('losses', 0)
            side = 'OVER' if hf_roi > 0 else 'UNDER'
            record = f"{wins}-{losses}" if side == 'OVER' else f"{losses}-{wins}"
            
            qualifying_criteria.append({
                'description': "When the home team's favored?",
                'side': side,
                'record': record,
                'roi': round(abs(hf_roi), 1)
            })
    
    # Check home underdog
    if 'home_underdog' in main_ou:
        home_dog = main_ou['home_underdog']
        hd_roi = home_dog.get('roi', 0)
        if abs(hd_roi) >= 5:
            wins = home_dog.get('wins', 0)
            losses = home_dog.get('losses', 0)
            side = 'OVER' if hd_roi > 0 else 'UNDER'
            record = f"{wins}-{losses}" if side == 'OVER' else f"{losses}-{wins}"
            
            qualifying_criteria.append({
                'description': "When the home team's an underdog?",
                'side': side,
                'record': record,
                'roi': round(abs(hd_roi), 1)
            })
    
    # Check conference games
    conf_roi = conf.get('in_conf_net_roi', 0)
    if abs(conf_roi) >= 5:
        wins = conf.get('in_conf_wins', 0)
        losses = conf.get('in_conf_losses', 0)
        side = 'OVER' if conf_roi > 0 else 'UNDER'
        record = f"{wins}-{losses}" if side == 'OVER' else f"{losses}-{wins}"
        
        qualifying_criteria.append({
            'description': 'When in-conference?',
            'side': side,
            'record': record,
            'roi': round(abs(conf_roi), 1)
        })
    
    # Check over_under_range
    range_roi = range_data.get('ou_range_roi', 0)
    if abs(range_roi) >= 5:
        wins = range_data.get('ou_range_wins', 0)
        losses = range_data.get('ou_range_losses', 0)
        ou_range = range_data.get('ou_range', 'specified range')
        
        # Format range text properly
        if ou_range and ' to ' in ou_range:
            range_parts = ou_range.split(' to ')
            range_text = f"{range_parts[0]} and {range_parts[1]}"
        else:
            range_text = ou_range
            
        side = 'OVER' if range_roi > 0 else 'UNDER'
        record = f"{wins}-{losses}" if side == 'OVER' else f"{losses}-{wins}"
        
        qualifying_criteria.append({
            'description': f'When total is between {range_text}?',
            'side': side,
            'record': record,
            'roi': round(abs(range_roi), 1)
        })
    
    # Need at least 3 criteria with 5%+ ROI
    if len(qualifying_criteria) < 3:
        return None
    
    # Sort by ROI descending
    qualifying_criteria.sort(key=lambda x: x['roi'], reverse=True)
    
    # Determine the dominant side
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
            
            edge_analysis = analyze_referee_over_under_edge(ref_stats, game)
            if edge_analysis:
                # Calculate max ROI for sorting
                max_roi = max(criteria['roi'] for criteria in edge_analysis['criteria'])
                
                # Convert team names to abbreviations
                home_abbrev = home_team.split()[-1][:3].upper()  # Get last word, first 3 chars
                away_abbrev = away_team.split()[-1][:3].upper()  # Get last word, first 3 chars
                
                game_edges.append({
                    'game_id': game_id,
                    'matchup': f"{away_abbrev} @ {home_abbrev}",
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
        side_text = f"{game['side'].lower()}s"  # "unders" or "overs"
        lines.append(f"🏈 Referee Report: Take this {game['side']}!")
        lines.append("")
        lines.append(f"{game['referee']} {side_text} ({game['matchup']}):")
        
        for criteria in game['criteria']:
            lines.append(f"{criteria['description']} {criteria['record']}, {criteria['roi']}% ROI")
        
        lines.append("")
        lines.append("Drop a ❤️ if you're tailing!")
        
    else:
        lines.append("🏈 Referee Report: Take these totals!")
        
        for game in game_edges:
            lines.append("")
            side_text = f"{game['side'].lower()}s"  # "unders" or "overs"
            lines.append(f"{game['referee']} {side_text} ({game['matchup']}):")
            
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
            print(f"🔍 Debug: Found {len(sport_data['big_bettor_alerts'])} {sport_name} picks, attempting to create tweet...")
            tweet_text = create_big_bettor_tweet_sanitized(sport_data, sport_name)
            tweet_type = f"{sport_name} Big Money Alert"
            
            print(f"🔍 Debug: Tweet created for {sport_name}: {'Yes' if tweet_text else 'No'}")
            if tweet_text:
                tweets_to_post.append((tweet_text, tweet_type))
            else:
                print(f"⚠️ {sport_name} tweet creation failed - likely date filtering issue")
    
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
