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

def get_insider_games(sport, days_ahead=0):
    """Fetch games from InsideRedge API for specified sport - same day only by default"""
    try:
        print(f"🔄 Starting API call for {sport}...")
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)

        from_date = today.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')

        url = f"{INSIDER_BASE_URL}/{sport.lower()}/games?from={from_date}&to={to_date}"
        print(f"🌐 Fetching {sport} games from {url}")
        print(f"🔑 Using API key: {INSIDER_API_KEY[:8]}...")
        
        # Add shorter timeout and better error handling
        print("⏱️ Making request with 10 second timeout...")
        response = requests.get(
            url, 
            headers={'insider-api-key': INSIDER_API_KEY}, 
            timeout=10  # Reduced from 30 to 10 seconds
        )
        
        print(f"✅ Got response: {response.status_code}")
        response.raise_for_status()

        data = response.json()
        games = data.get('games', [])
        print(f"✅ Parsed {len(games)} {sport} games successfully")

        return games
    except requests.exceptions.Timeout:
        print(f"⏰ TIMEOUT: {sport} API call took longer than 10 seconds")
        return []
    except requests.exceptions.ConnectionError:
        print(f"🌐 CONNECTION ERROR: Could not connect to {sport} API")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"🚫 HTTP ERROR for {sport}: {e}")
        print(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
        return []
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR fetching {sport} games: {e}")
        return []

def convert_insider_to_big_bettor_format(games, sport):
    """Convert InsideRedge game data to big bettor alert format - DEBUG VERSION"""
    big_bettor_alerts = []
    
    print(f"🔍 DEBUG: Processing {len(games)} {sport} games for big bettor alerts...")
    
    for i, game in enumerate(games, 1):
        try:
            public_money = game.get('public_money_stats', {})
            odds = game.get('odds', {})
            
            # Extract team info
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            game_date = game.get('game_date', '')
            
            print(f"\n--- Game {i}: {away_team} @ {home_team} ---")
            
            # Check if we have public money data
            if not public_money:
                print("❌ No public_money_stats found")
                continue
                
            print("✅ Found public money stats")
            
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

            print(f"Spread: {spread}")

            # Process spread bets for both teams
            spread_away_bets = public_money.get('public_money_spread_away_bets_pct', 0)
            spread_away_stake = public_money.get('public_money_spread_away_stake_pct', 0)
            spread_home_bets = public_money.get('public_money_spread_home_bets_pct', 0)
            spread_home_stake = public_money.get('public_money_spread_home_stake_pct', 0)
            
            print(f"Away Spread - Bets: {spread_away_bets}%, Handle: {spread_away_stake}%, Diff: {spread_away_stake - spread_away_bets}")
            print(f"Home Spread - Bets: {spread_home_bets}%, Handle: {spread_home_stake}%, Diff: {spread_home_stake - spread_home_bets}")
            
            # Check away team spread (they get + spread) - LOWERED THRESHOLD TO 15
            away_diff = spread_away_stake - spread_away_bets
            if away_diff >= 15:  # Lowered from 30 to 15
                print(f"🔥 ALERT: {away_team} spread meets criteria!")
                away_spread_display = f"+{abs(spread)}" if spread < 0 else f"+{spread}"
                big_bettor_alerts.append({
                    'team': away_team,
                    'odds': f"{away_spread_display} ({away_spread_odds:+d})",
                    'bets_pct': f"{spread_away_bets}%",
                    'handle_pct': f"{spread_away_stake}%",
                    'game_time': game_time
                })
            
            # Check home team spread (they get - spread) - LOWERED THRESHOLD TO 15
            home_diff = spread_home_stake - spread_home_bets
            if home_diff >= 15:  # Lowered from 30 to 15
                print(f"🔥 ALERT: {home_team} spread meets criteria!")
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
            
            print(f"Away ML - Bets: {ml_away_bets}%, Handle: {ml_away_stake}%, Diff: {ml_away_stake - ml_away_bets}")
            print(f"Home ML - Bets: {ml_home_bets}%, Handle: {ml_home_stake}%, Diff: {ml_home_stake - ml_home_bets}")
            
            # Check away team moneyline - LOWERED THRESHOLD TO 15
            away_ml_diff = ml_away_stake - ml_away_bets
            if away_ml_diff >= 15:  # Lowered from 30 to 15
                print(f"🔥 ALERT: {away_team} ML meets criteria!")
                big_bettor_alerts.append({
                    'team': away_team,
                    'odds': f"ML ({away_ml:+d})",
                    'bets_pct': f"{ml_away_bets}%",
                    'handle_pct': f"{ml_away_stake}%",
                    'game_time': game_time
                })
            
            # Check home team moneyline - LOWERED THRESHOLD TO 15
            home_ml_diff = ml_home_stake - ml_home_bets
            if home_ml_diff >= 15:  # Lowered from 30 to 15
                print(f"🔥 ALERT: {home_team} ML meets criteria!")
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
    
    print(f"\n🎯 SUMMARY: Found {len(big_bettor_alerts)} qualifying big bettor alerts")
    
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
        print(f"⚠️ No big bettor alerts found for {sport}")
        return None
    
    picks = data['big_bettor_alerts']
    
    if not picks:
        print(f"⚠️ Empty picks list for {sport}")
        return None
    
    print(f"🎯 Creating tweet for {len(picks)} {sport} picks")
    
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
            
        except (ValueError, KeyError) as e:
            print(f"❌ Error formatting pick: {e}")
            continue
    
    lines.append("Drop a ❤️ if you're taking any of these!")
    
    tweet_text = '\n'.join(lines)
    print(f"✅ Created {sport} tweet: {len(tweet_text)} characters")
    return tweet_text

def get_todays_mlb_games():
    """Fetch today's MLB games"""
    try:
        print(f"🔄 Starting MLB games API call...")
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{INSIDER_BASE_URL}/mlb/games?from={today}&to={today}"
        
        print(f"🌐 MLB URL: {url}")
        print("⏱️ Making MLB request with 10 second timeout...")
        
        response = requests.get(
            url, 
            headers={'insider-api-key': INSIDER_API_KEY}, 
            timeout=10
        )
        
        print(f"✅ MLB response: {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        games = data.get('games', [])
        print(f"✅ Got {len(games)} MLB games for today")
        return games
    except requests.exceptions.Timeout:
        print(f"⏰ TIMEOUT: MLB games API call took longer than 10 seconds")
        return []
    except requests.exceptions.ConnectionError:
        print(f"🌐 CONNECTION ERROR: Could not connect to MLB games API")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"🚫 HTTP ERROR for MLB games: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching MLB games: {e}")
        return []

def get_todays_nfl_games():
    """Fetch today's NFL games"""
    try:
        print(f"🔄 Starting NFL games API call...")
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{INSIDER_BASE_URL}/nfl/games?from={today}&to={today}"
        
        print(f"🌐 NFL URL: {url}")
        print("⏱️ Making NFL request with 10 second timeout...")
        
        response = requests.get(
            url, 
            headers={'insider-api-key': INSIDER_API_KEY}, 
            timeout=10
        )
        
        print(f"✅ NFL response: {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        games = data.get('games', [])
        print(f"✅ Got {len(games)} NFL games for today")
        return games
    except requests.exceptions.Timeout:
        print(f"⏰ TIMEOUT: NFL games API call took longer than 10 seconds")
        return []
    except requests.exceptions.ConnectionError:
        print(f"🌐 CONNECTION ERROR: Could not connect to NFL games API")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"🚫 HTTP ERROR for NFL games: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching NFL games: {e}")
        return []

def get_referee_stats(game_id):
    """Fetch referee stats for a specific NFL game"""
    try:
        print(f"🔄 Fetching referee stats for {game_id}...")
        url = f"{INSIDER_BASE_URL}/nfl/games/{game_id}/referee-stats"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=10)
        print(f"✅ Referee stats response for {game_id}: {response.status_code}")
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching referee stats for {game_id}: {e}")
        return None

def analyze_referee_over_under_edge(ref_stats, game=None, is_home_favored=None):
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
    
    # Check home favorite/underdog stats if applicable
    if is_home_favored and 'home_favorite' in main_ou:
        home_fav = main_ou['home_favorite']
        hf_roi = home_fav.get('roi', 0)
        if abs(hf_roi) >= 5:
            wins = home_fav.get('wins', 0)
            losses = home_fav.get('losses', 0)
            side = 'OVER' if hf_roi > 0 else 'UNDER'
            record = f"{wins}-{losses}" if side == 'OVER' else f"{losses}-{wins}"
            
            qualifying_criteria.append({
                'description': "When the home team's favored",
                'side': side,
                'record': record,
                'roi': round(abs(hf_roi), 1)
            })
    
    if is_home_favored is False and 'home_underdog' in main_ou:
        home_dog = main_ou['home_underdog']
        hd_roi = home_dog.get('roi', 0)
        if abs(hd_roi) >= 5:
            wins = home_dog.get('wins', 0)
            losses = home_dog.get('losses', 0)
            side = 'OVER' if hd_roi > 0 else 'UNDER'
            record = f"{wins}-{losses}" if side == 'OVER' else f"{losses}-{wins}"
            
            qualifying_criteria.append({
                'description': "When the home team's an underdog",
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
            'description': 'When in-conference',
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
            'description': f'When total is between {range_text}',
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
    print("🔄 Starting referee analysis...")
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

def get_player_props(game_id):
    """Fetch player props for a specific game"""
    try:
        print(f"🔄 Fetching props for game {game_id}...")
        url = f"{INSIDER_BASE_URL}/mlb/games/{game_id}/player-props"
        
        print(f"🌐 Props URL: {url}")
        print("⏱️ Making props request with 10 second timeout...")
        
        response = requests.get(
            url, 
            headers={'insider-api-key': INSIDER_API_KEY}, 
            timeout=10
        )
        
        print(f"✅ Props response for {game_id}: {response.status_code}")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Got props data for {game_id}")
        return data
    except requests.exceptions.Timeout:
        print(f"⏰ TIMEOUT: Props API call for {game_id} took longer than 10 seconds")
        return None
    except requests.exceptions.ConnectionError:
        print(f"🌐 CONNECTION ERROR: Could not connect to props API for {game_id}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"🚫 HTTP ERROR for props {game_id}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error fetching props for {game_id}: {e}")
        return None

def create_mlb_prop_hit_rates_tweet():
    """Create tweet for MLB props with 70%+ hit rates"""
    print("🔄 Starting MLB prop hit rates analysis...")
    
    games = get_todays_mlb_games()
    if not games:
        print("❌ No MLB games found, skipping prop analysis")
        return None
        
    print(f"🎯 Analyzing props for {len(games)} games...")
    all_props = []
    
    for i, game in enumerate(games, 1):
        try:
            game_id = game['game_id']
            print(f"📊 Processing game {i}/{len(games)}: {game_id}")
            
            props_data = get_player_props(game_id)
            
            if not props_data or not isinstance(props_data, list):
                print(f"⚠️ No valid props data for {game_id}")
                continue
                
            print(f"✅ Found {len(props_data)} prop categories for {game_id}")
            
            # Process props...
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
                                    
                    except (KeyError, TypeError, ZeroDivisionError) as e:
                        print(f"⚠️ Error processing player prop: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Error processing game {game.get('name', 'Unknown')}: {e}")
            continue
    
    print(f"🎯 Found {len(all_props)} qualifying props")
    
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
        
        print(f"🐦 Attempting to post {tweet_type} ({len(text)} chars)")
        
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
    print("\n🎯 ANALYZING BIG BETTOR ALERTS...")
    for sport_name, display_name in sports:
        print(f"\n--- Processing {sport_name} ---")
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
            else:
                print(f"⚠️ No big bettor alerts found for {sport_name}")
        else:
            print(f"⚠️ No games found for {sport_name}")

    # Add MLB prop hit rates tweet
    print(f"\n--- Processing MLB Props ---")
    mlb_props_tweet = create_mlb_prop_hit_rates_tweet()
    if mlb_props_tweet:
        tweets_to_post.append((mlb_props_tweet, "MLB Prop Hit Rates"))

    # Add NFL referee report tweet
    print(f"\n--- Processing NFL Referee Report ---")
    nfl_referee_tweet = create_referee_tweet()
    if nfl_referee_tweet:
        tweets_to_post.append((nfl_referee_tweet, "NFL Referee Report"))

    # Post tweets with delays
    print(f"\n🐦 POSTING TWEETS...")
    successful_posts = 0
    total_attempts = len(tweets_to_post)
    
    if total_attempts == 0:
        print("⚠️ No tweets to post - no qualifying content found")
        return

    for i, (tweet_text, tweet_type) in enumerate(tweets_to_post):
        print(f"\n--- Attempting to post {tweet_type} ({i+1}/{total_attempts}) ---")
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
