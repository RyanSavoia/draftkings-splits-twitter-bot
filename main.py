import json
import requests
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email credentials from environment variables
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECIPIENTS = ['ryansavoia7@gmail.com', 'sean@thebettinginsider.com']

# InsideRedge API credentials
INSIDER_API_KEY = "5c2f9307-ea6c-4a9c-8d8b-b09643a60bfd"
INSIDER_BASE_URL = "https://commercial.insideredgeanalytics.com/api"

# NFL Team name to abbreviation mapping
NFL_TEAM_ABBREVIATIONS = {
    'Arizona Cardinals': 'ARI',
    'Atlanta Falcons': 'ATL', 
    'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF',
    'Carolina Panthers': 'CAR',
    'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN',
    'Cleveland Browns': 'CLE',
    'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN',
    'Detroit Lions': 'DET',
    'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU',
    'Indianapolis Colts': 'IND',
    'Jacksonville Jaguars': 'JAX',
    'Kansas City Chiefs': 'KC',
    'Miami Dolphins': 'MIA',
    'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE',
    'New Orleans Saints': 'NO',
    'New York Giants': 'NYG',
    'New York Jets': 'NYJ',
    'Las Vegas Raiders': 'LV',
    'Philadelphia Eagles': 'PHI',
    'Pittsburgh Steelers': 'PIT',
    'Los Angeles Chargers': 'LAC',
    'San Francisco 49ers': 'SF',
    'Seattle Seahawks': 'SEA',
    'Los Angeles Rams': 'LAR',
    'Tampa Bay Buccaneers': 'TB',
    'Tennessee Titans': 'TEN',
    'Washington Commanders': 'WAS'
}

def get_team_abbreviation(team_name):
    """Convert full team name to official NFL abbreviation"""
    return NFL_TEAM_ABBREVIATIONS.get(team_name, team_name[:3].upper())

def get_insider_games(sport, days_ahead=0):
    """Fetch games from InsideRedge API for specified sport"""
    try:
        print(f"🔄 Starting API call for {sport}...")
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)

        from_date = today.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')

        url = f"{INSIDER_BASE_URL}/{sport.lower()}/games?from={from_date}&to={to_date}"
        print(f"🌐 Fetching {sport} games from {url}")
        
        response = requests.get(
            url, 
            headers={'insider-api-key': INSIDER_API_KEY}, 
            timeout=10
        )
        
        print(f"✅ Got response: {response.status_code}")
        response.raise_for_status()

        data = response.json()
        games = data.get('games', [])
        print(f"✅ Parsed {len(games)} {sport} games successfully")

        return games
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR fetching {sport} games: {e}")
        return []

def get_public_money_data(game_id, sport='mlb'):
    """Fetch public money data for a specific game"""
    try:
        url = f"{INSIDER_BASE_URL}/{sport}/games/{game_id}/public-money"
        
        response = requests.get(
            url, 
            headers={'insider-api-key': INSIDER_API_KEY}, 
            timeout=10
        )
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching public money for {game_id}: {e}")
        return None

def convert_insider_to_big_bettor_format(games, sport):
    """Convert InsideRedge game data to big bettor alert format"""
    big_bettor_alerts = []
    
    print(f"🔍 Processing {len(games)} {sport} games for big bettor alerts...")
    
    for i, game in enumerate(games, 1):
        try:
            game_id = game.get('game_id', '')
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            game_date = game.get('game_date', '')
            odds = game.get('odds', {})
            
            print(f"\n--- Game {i}: {away_team} @ {home_team} ({game_id}) ---")
            
            # Get public money data via separate API call
            public_money = get_public_money_data(game_id, sport.lower())
            
            if not public_money:
                print("❌ No public money data found")
                continue
                
            print("✅ Found public money data")
            
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
            away_diff = spread_away_stake - spread_away_bets
            if away_diff >= 25:
                print(f"🔥 ALERT: {away_team} spread meets criteria!")
                away_spread_display = f"+{abs(spread)}" if spread < 0 else f"+{spread}"
                big_bettor_alerts.append({
                    'team': away_team,
                    'odds': f"{away_spread_display} ({away_spread_odds:+d})",
                    'bets_pct': f"{spread_away_bets}%",
                    'handle_pct': f"{spread_away_stake}%",
                    'game_time': game_time
                })
            
            # Check home team spread (they get - spread)
            home_diff = spread_home_stake - spread_home_bets
            if home_diff >= 25:
                print(f"🔥 ALERT: {home_team} spread meets criteria!")
                home_spread_display = f"-{abs(spread)}" if spread > 0 else f"{spread}"
                big_bettor_alerts.append({
                    'team': home_team,
                    'odds': f"{home_spread_display} ({home_spread_odds:+d})",
                    'bets_pct': f"{spread_home_bets}%",
                    'handle_pct': f"{spread_home_stake}%",
                    'game_time': game_time
                })
            
            # Process moneyline bets
            ml_away_bets = public_money.get('public_money_ml_away_bets_pct', 0)
            ml_away_stake = public_money.get('public_money_ml_away_stake_pct', 0)
            ml_home_bets = public_money.get('public_money_ml_home_bets_pct', 0)
            ml_home_stake = public_money.get('public_money_ml_home_stake_pct', 0)
            
            away_ml = odds.get('away_team_odds', {}).get('moneyline', 0)
            home_ml = odds.get('home_team_odds', {}).get('moneyline', 0)
            
            # Check away team moneyline
            away_ml_diff = ml_away_stake - ml_away_bets
            if away_ml_diff >= 25:
                print(f"🔥 ALERT: {away_team} ML meets criteria!")
                big_bettor_alerts.append({
                    'team': away_team,
                    'odds': f"ML ({away_ml:+d})",
                    'bets_pct': f"{ml_away_bets}%",
                    'handle_pct': f"{ml_away_stake}%",
                    'game_time': game_time
                })
            
            # Check home team moneyline
            home_ml_diff = ml_home_stake - ml_home_bets
            if home_ml_diff >= 25:
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

def create_big_bettor_tweet_text(data, sport):
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
            
        except (ValueError, KeyError) as e:
            print(f"❌ Error formatting pick: {e}")
            continue
    
    lines.append("Drop a ❤️ if you're taking any of these!")
    
    return '\n'.join(lines)

def get_player_props(game_id, sport='mlb'):
    """Fetch player props for a specific game"""
    try:
        url = f"{INSIDER_BASE_URL}/{sport}/games/{game_id}/player-props"
        
        response = requests.get(
            url, 
            headers={'insider-api-key': INSIDER_API_KEY}, 
            timeout=10
        )
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching props for {game_id}: {e}")
        return None

def create_prop_hit_rates_tweet(sport='MLB'):
    """Create tweet for props with 65%+ hit rates for NFL, 70%+ for MLB"""
    print(f"🔄 Starting {sport} prop hit rates analysis...")
    
    games = get_insider_games(sport)
    if not games:
        print(f"❌ No {sport} games found, skipping prop analysis")
        return None
        
    print(f"🎯 Analyzing props for {len(games)} games...")
    all_props = []
    
    # Set threshold based on sport
    threshold = 65 if sport.upper() == 'NFL' else 70
    
    for i, game in enumerate(games, 1):
        try:
            game_id = game['game_id']
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            print(f"📊 Processing game {i}/{len(games)}: {game_id}")
            
            props_data = get_player_props(game_id, sport.lower())
            
            if not props_data or not isinstance(props_data, list):
                print(f"⚠️ No valid props data for {game_id}")
                continue
                
            print(f"✅ Found {len(props_data)} prop categories for {game_id}")
            
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
                        
                        # Get actual odds and sportsbook from best_line
                        best_line = player.get('best_line', {})
                        current_odds = best_line.get('opening_odds', -110)
                        sportsbook = best_line.get('bookmaker', 'Unknown')
                        
                        # Determine which team the player is on
                        # This is a simplification - you might need more sophisticated logic
                        # to match players to teams accurately
                        player_team = "Unknown"
                        
                        # Skip UNDER props except for strikeouts and pitcher outs (MLB) or specific NFL props
                        if sport.upper() == 'MLB':
                            if prop_type == "under" and prop_key not in ["pitcher_strikeouts", "pitcher_outs"]:
                                continue
                        
                        if isinstance(record, dict):
                            hit = record.get('hit', 0)
                            miss = record.get('miss', 0)
                            total = record.get('total', 0)
                            
                            if total >= 20:  # Minimum sample size
                                hit_rate = (hit / total) * 100
                                
                                if hit_rate >= threshold:  # Use dynamic threshold
                                    # Clean up prop title
                                    prop_clean = prop_title.replace(' (Over/Under)', '').replace(' (Yes/No)', '').replace('Batter ', '').replace('Pitcher ', '')
                                    
                                    # Format sportsbook name
                                    book_display = sportsbook.title() if sportsbook != 'Unknown' else ''
                                    
                                    # Format prop description with exact API values
                                    if prop_type.lower() == "over":
                                        prop_description = f"{player_name} Over {opening_line} {prop_clean} ({current_odds:+d} {book_display})"
                                    elif prop_type.lower() == "under":
                                        prop_description = f"{player_name} Under {opening_line} {prop_clean} ({current_odds:+d} {book_display})"
                                    else:
                                        prop_description = f"{player_name} {prop_type.title()} {opening_line} {prop_clean} ({current_odds:+d} {book_display})"
                                    
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
        print(f"⚠️ No {sport} props found with {threshold}%+ hit rates")
        return None
    
    # Sort by hit rate and take top 5
    all_props.sort(key=lambda x: x['hit_rate'], reverse=True)
    top_props = all_props[:5]
    
    lines = []
    # Updated headline for NFL
    if sport.upper() == 'NFL':
        lines.append(f"These 65%+ {sport} props are must adds to your parlays! 🏈")
    else:
        lines.append(f"These 70%+ {sport} props are must adds to your parlays! ⚾")
    lines.append("")
    
    for i, prop in enumerate(top_props, 1):
        hit_rate_formatted = f"{prop['hit_rate']:.1f}%"
        lines.append(f"{i}. {prop['description']}")
        lines.append(f"   {hit_rate_formatted} ({prop['record']} this season)")
        lines.append("")
    
    lines.append("Drop a ❤️ if you're taking any of these!")
    
    return '\n'.join(lines)

def get_referee_stats(game_id):
    """Fetch referee stats for a specific NFL game"""
    try:
        url = f"{INSIDER_BASE_URL}/nfl/games/{game_id}/referee-stats"
        
        response = requests.get(url, headers={'insider-api-key': INSIDER_API_KEY}, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching referee stats for {game_id}: {e}")
        return None

def analyze_referee_spread_edge(ref_stats, game=None, is_home_favored=None):
    """Analyze referee stats to find SPREAD edges with 5%+ ROI in 3+ criteria"""
    if not ref_stats or 'referee_odds' not in ref_stats or 'spread' not in ref_stats['referee_odds']:
        return None
    
    spread_data = ref_stats['referee_odds']['spread']
    qualifying_criteria = []
    
    # Get main sections
    main_spread = spread_data.get('spread', {})
    conf = spread_data.get('conference', {})
    range_data = spread_data.get('spread_range', {})
    
    # Check overall ATS ROI - this represents the referee's overall impact on spread betting
    ats_roi = main_spread.get('ats_roi', 0)
    if abs(ats_roi) >= 5:
        ats_wins = main_spread.get('ats_wins', 0)
        ats_losses = main_spread.get('ats_losses', 0)
        side = 'FAVORITES' if ats_roi > 0 else 'DOGS'
        record = f"{ats_wins}-{ats_losses}"
        qualifying_criteria.append({
            'description': 'Home teams overall ATS historically?',
            'side': side,
            'record': record,
            'roi': round(abs(ats_roi), 1)
        })
    
    # Check home favorite ATS performance
    home_fav_roi = main_spread.get('home_favorite_net_roi', 0)
    if abs(home_fav_roi) >= 5:
        home_fav_wins = main_spread.get('home_favorite_wins', 0)
        home_fav_losses = main_spread.get('home_favorite_losses', 0)
        side = 'HOME FAVORITES' if home_fav_roi > 0 else 'HOME DOGS'
        record = f"{home_fav_wins}-{home_fav_losses}" if home_fav_roi > 0 else f"{home_fav_losses}-{home_fav_wins}"
        
        qualifying_criteria.append({
            'description': 'Home favorites ATS?',
            'side': side,
            'record': record,
            'roi': round(abs(home_fav_roi), 1)
        })
    
    # Check conference games ATS
    conf_roi = conf.get('out_conf_net_roi', 0)
    if abs(conf_roi) >= 5:
        conf_wins = conf.get('out_conf_wins', 0)
        conf_losses = conf.get('out_conf_losses', 0)
        side = 'OUT-OF-CONF' if conf_roi > 0 else 'IN-CONF'
        record = f"{conf_wins}-{conf_losses}" if conf_roi > 0 else f"{conf_losses}-{conf_wins}"
        
        qualifying_criteria.append({
            'description': 'Out of conference ATS?',
            'side': side,
            'record': record,
            'roi': round(abs(conf_roi), 1)
        })
    
    # Check spread range performance
    away_range_roi = range_data.get('away_spread_range_roi', 0)
    if abs(away_range_roi) >= 5:
        away_range_wins = range_data.get('away_spread_range_wins', 0)
        away_range_losses = range_data.get('away_spread_range_losses', 0)
        away_range_desc = range_data.get('away_spread_range', 'away spread range')
        
        side = 'AWAY TEAMS' if away_range_roi > 0 else 'HOME TEAMS'
        record = f"{away_range_wins}-{away_range_losses}" if away_range_roi > 0 else f"{away_range_losses}-{away_range_wins}"
        
        qualifying_criteria.append({
            'description': f'Away teams when spread is {away_range_desc}?',
            'side': side,
            'record': record,
            'roi': round(abs(away_range_roi), 1)
        })
    
    home_range_roi = range_data.get('home_spread_range_roi', 0)
    if abs(home_range_roi) >= 5:
        home_range_wins = range_data.get('home_spread_range_wins', 0)
        home_range_losses = range_data.get('home_spread_range_losses', 0)
        home_range_desc = range_data.get('home_spread_range', 'home spread range')
        
        side = 'HOME TEAMS' if home_range_roi > 0 else 'AWAY TEAMS'
        record = f"{home_range_wins}-{home_range_losses}" if home_range_roi > 0 else f"{home_range_losses}-{home_range_wins}"
        
        qualifying_criteria.append({
            'description': f'Home teams when spread is {home_range_desc}?',
            'side': side,
            'record': record,
            'roi': round(abs(home_range_roi), 1)
        })
    
    # Need at least 3 criteria with 5%+ ROI
    if len(qualifying_criteria) < 3:
        return None
    
    # Sort by ROI descending
    qualifying_criteria.sort(key=lambda x: x['roi'], reverse=True)
    
    # Determine the dominant side (most common recommendation)
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

def analyze_referee_moneyline_edge(ref_stats, game=None, is_home_favored=None):
    """Analyze referee stats to find MONEYLINE edges with 5%+ ROI in 3+ criteria"""
    if not ref_stats or 'referee_odds' not in ref_stats or 'moneyline' not in ref_stats['referee_odds']:
        return None
    
    ml_data = ref_stats['referee_odds']['moneyline']
    qualifying_criteria = []
    
    # Get main sections
    main_ml = ml_data.get('ml', {})
    conf = ml_data.get('conference', {})
    range_data = ml_data.get('ml_range', {})
    
    # Check home ML performance
    home_ml_roi = main_ml.get('home_ml_roi', 0)
    if abs(home_ml_roi) >= 5:
        home_ml_wins = main_ml.get('home_ml_wins', 0)
        home_ml_losses = main_ml.get('home_ml_losses', 0)
        side = 'HOME TEAMS' if home_ml_roi > 0 else 'AWAY TEAMS'
        record = f"{home_ml_wins}-{home_ml_losses}" if home_ml_roi > 0 else f"{home_ml_losses}-{home_ml_wins}"
        
        qualifying_criteria.append({
            'description': 'Home teams ML?',
            'side': side,
            'record': record,
            'roi': round(abs(home_ml_roi), 1)
        })
    
    # Check home favorite ML performance
    home_fav_roi = main_ml.get('home_favorite_net_roi', 0)
    if abs(home_fav_roi) >= 5:
        home_fav_wins = main_ml.get('home_favorite_wins', 0)
        home_fav_losses = main_ml.get('home_favorite_losses', 0)
        side = 'HOME FAVORITES' if home_fav_roi > 0 else 'HOME DOGS'
        record = f"{home_fav_wins}-{home_fav_losses}" if home_fav_roi > 0 else f"{home_fav_losses}-{home_fav_wins}"
        
        qualifying_criteria.append({
            'description': 'Home favorites ML?',
            'side': side,
            'record': record,
            'roi': round(abs(home_fav_roi), 1)
        })
    
    # Check conference games ML
    conf_roi = conf.get('out_conf_net_roi', 0)
    if abs(conf_roi) >= 5:
        conf_wins = conf.get('out_conf_wins', 0)
        conf_losses = conf.get('out_conf_losses', 0)
        side = 'OUT-OF-CONF' if conf_roi > 0 else 'IN-CONF'
        record = f"{conf_wins}-{conf_losses}" if conf_roi > 0 else f"{conf_losses}-{conf_wins}"
        
        qualifying_criteria.append({
            'description': 'Out of conference ML?',
            'side': side,
            'record': record,
            'roi': round(abs(conf_roi), 1)
        })
    
    # Check ML range performance
    away_ml_roi = range_data.get('away_ml_range_roi', 0)
    if abs(away_ml_roi) >= 5:
        away_ml_wins = range_data.get('away_ml_range_wins', 0)
        away_ml_losses = range_data.get('away_ml_range_losses', 0)
        away_ml_range = range_data.get('away_ml_range', 'away ML range')
        
        side = 'AWAY DOGS' if away_ml_roi > 0 else 'AWAY FAVORITES'
        record = f"{away_ml_wins}-{away_ml_losses}" if away_ml_roi > 0 else f"{away_ml_losses}-{away_ml_wins}"
        
        qualifying_criteria.append({
            'description': f'Away ML when odds are {away_ml_range}?',
            'side': side,
            'record': record,
            'roi': round(abs(away_ml_roi), 1)
        })
    
    home_ml_range_roi = range_data.get('home_ml_range_roi', 0)
    if abs(home_ml_range_roi) >= 5:
        home_ml_range_wins = range_data.get('home_ml_range_wins', 0)
        home_ml_range_losses = range_data.get('home_ml_range_losses', 0)
        home_ml_range = range_data.get('home_ml_range', 'home ML range')
        
        side = 'HOME FAVORITES' if home_ml_range_roi > 0 else 'HOME DOGS'
        record = f"{home_ml_range_wins}-{home_ml_range_losses}" if home_ml_range_roi > 0 else f"{home_ml_range_losses}-{home_ml_wins}"
        
        qualifying_criteria.append({
            'description': f'Home ML when odds are {home_ml_range}?',
            'side': side,
            'record': record,
            'roi': round(abs(home_ml_range_roi), 1)
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
            'description': 'Overall?',
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
            'description': 'Overall?',
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
                'description': "When the home team's favored?",
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
    
    # Check over_under_range - only include if sufficient sample size (5+ games)
    range_roi = range_data.get('ou_range_roi', 0)
    range_wins = range_data.get('ou_range_wins', 0)
    range_losses = range_data.get('ou_range_losses', 0)
    range_total_games = range_wins + range_losses
    
    if abs(range_roi) >= 5 and range_total_games >= 5:
        ou_range = range_data.get('ou_range', 'specified range')
        
        # Format range text properly
        if ou_range and ' to ' in ou_range:
            range_parts = ou_range.split(' to ')
            range_text = f"{range_parts[0]} and {range_parts[1]}"
        else:
            range_text = ou_range
            
        side = 'OVER' if range_roi > 0 else 'UNDER'
        record = f"{range_wins}-{range_losses}" if side == 'OVER' else f"{range_losses}-{range_wins}"
        
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
    """Create referee report tweet for NFL games - TOTALS"""
    print("🔄 Starting referee totals analysis...")
    games = get_insider_games('NFL')
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
                
                # Convert team names to proper abbreviations
                home_abbrev = get_team_abbreviation(home_team)
                away_abbrev = get_team_abbreviation(away_team)
                
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

def create_referee_spread_tweet():
    """Create referee spread report tweet for NFL games"""
    print("🔄 Starting referee spread analysis...")
    games = get_insider_games('NFL')
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
            
            edge_analysis = analyze_referee_spread_edge(ref_stats)
            if edge_analysis:
                # Calculate max ROI for sorting
                max_roi = max(criteria['roi'] for criteria in edge_analysis['criteria'])
                
                # Convert team names to proper abbreviations
                home_abbrev = get_team_abbreviation(home_team)
                away_abbrev = get_team_abbreviation(away_team)
                
                game_edges.append({
                    'game_id': game_id,
                    'matchup': f"{away_abbrev} @ {home_abbrev}",
                    'referee': referee_name,
                    'side': edge_analysis['side'],
                    'criteria': edge_analysis['criteria'],
                    'max_roi': max_roi
                })
                
        except Exception as e:
            print(f"❌ Error processing referee spread stats for game {game.get('name', 'Unknown')}: {e}")
            continue
    
    if not game_edges:
        print("⚠️ No NFL games found with significant referee spread edges")
        return None
    
    # Sort by max ROI and limit to top 5
    game_edges.sort(key=lambda x: x['max_roi'], reverse=True)
    game_edges = game_edges[:5]
    
    lines = []
    
    # Single game vs multiple games logic - FIXED
    if len(game_edges) == 1:
        game = game_edges[0]
        lines.append(f"🏈 Referee Report: Take this spread!")
        lines.append("")
        lines.append(f"{game['referee']} Spreads ({game['matchup']}):")
        
        for criteria in game['criteria']:
            lines.append(f"{criteria['description']} {criteria['record']}, {criteria['roi']}% ROI")
        
        lines.append("")
        lines.append("Drop a ❤️ if you're tailing!")
        
    else:
        lines.append("🏈 Referee Report: Take these spreads!")
        
        for game in game_edges:
            lines.append("")
            lines.append(f"{game['referee']} Spreads ({game['matchup']}):")
            
            for criteria in game['criteria']:
                lines.append(f"{criteria['description']} {criteria['record']}, {criteria['roi']}% ROI")
        
        lines.append("")
        lines.append("Drop a ❤️ if you're tailing!")
    
    return '\n'.join(lines)

def create_referee_moneyline_tweet():
    """Create referee moneyline report tweet for NFL games"""
    print("🔄 Starting referee moneyline analysis...")
    games = get_insider_games('NFL')
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
            
            edge_analysis = analyze_referee_moneyline_edge(ref_stats)
            if edge_analysis:
                # Calculate max ROI for sorting
                max_roi = max(criteria['roi'] for criteria in edge_analysis['criteria'])
                
                # Convert team names to proper abbreviations
                home_abbrev = get_team_abbreviation(home_team)
                away_abbrev = get_team_abbreviation(away_team)
                
                game_edges.append({
                    'game_id': game_id,
                    'matchup': f"{away_abbrev} @ {home_abbrev}",
                    'referee': referee_name,
                    'side': edge_analysis['side'],
                    'criteria': edge_analysis['criteria'],
                    'max_roi': max_roi
                })
                
        except Exception as e:
            print(f"❌ Error processing referee moneyline stats for game {game.get('name', 'Unknown')}: {e}")
            continue
    
    if not game_edges:
        print("⚠️ No NFL games found with significant referee moneyline edges")
        return None
    
    # Sort by max ROI and limit to top 5
    game_edges.sort(key=lambda x: x['max_roi'], reverse=True)
    game_edges = game_edges[:5]
    
    lines = []
    
    # Single game vs multiple games logic
    if len(game_edges) == 1:
        game = game_edges[0]
        lines.append(f"🏈 Referee Report: Take these moneylines!")
        lines.append("")
        lines.append(f"{game['referee']} straight up ({game['matchup']}):")
        
        for criteria in game['criteria']:
            lines.append(f"{criteria['description']} {criteria['record']}, {criteria['roi']}% ROI")
        
        lines.append("")
        lines.append("Drop a ❤️ if you're tailing!")
        
    else:
        lines.append("🏈 Referee Report: Take these moneylines!")
        
        for game in game_edges:
            lines.append("")
            lines.append(f"{game['referee']} straight up ({game['matchup']}):")
            
            for criteria in game['criteria']:
                lines.append(f"{criteria['description']} {criteria['record']}, {criteria['roi']}% ROI")
        
        lines.append("")
        lines.append("Drop a ❤️ if you're tailing!")
    
    return '\n'.join(lines)

def send_email(subject, body):
    """Send email with betting content"""
    try:
        print(f"📧 Sending email: {subject}")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ", ".join(EMAIL_RECIPIENTS)
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Gmail SMTP configuration
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {EMAIL_RECIPIENTS}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def run_betting_analysis():
    """Main function to generate and send betting analysis via email"""
    print(f"\n{'='*50}")
    print(f"Starting Betting Analysis at {datetime.now()}")
    print(f"{'='*50}")

    # Sports available from InsideRedge API  
    sports = [
        ('MLB', 'MLB'),
        ('NFL', 'NFL')
    ]

    # Collect all content to email
    email_content = []
    email_content.append(f"Daily Betting Analysis - {datetime.now().strftime('%Y-%m-%d')}")
    email_content.append("="*50)
    
    # Get big bettor alerts for each sport
    print("\n🎯 ANALYZING BIG BETTOR ALERTS...")
    for sport_name, display_name in sports:
        print(f"\n--- Processing {sport_name} ---")
        games = get_insider_games(sport_name)
        if games:
            big_bettor_alerts = convert_insider_to_big_bettor_format(games, sport_name)
            if big_bettor_alerts:
                sport_data = {'big_bettor_alerts': big_bettor_alerts}
                tweet_text = create_big_bettor_tweet_text(sport_data, display_name)
                    
                if tweet_text:
                    email_content.append(f"\n\n{display_name} BIG MONEY ALERTS:")
                    email_content.append("-" * 30)
                    email_content.append(tweet_text)
            else:
                print(f"⚠️ No big bettor alerts found for {sport_name}")
        else:
            print(f"⚠️ No games found for {sport_name}")

    # Add prop hit rates for both MLB and NFL
    print(f"\n--- Processing MLB Props ---")
    mlb_props_tweet = create_prop_hit_rates_tweet('MLB')
    if mlb_props_tweet:
        email_content.append(f"\n\nMLB PROP PICKS:")
        email_content.append("-" * 30)
        email_content.append(mlb_props_tweet)

    print(f"\n--- Processing NFL Props ---")
    nfl_props_tweet = create_prop_hit_rates_tweet('NFL')
    if nfl_props_tweet:
        email_content.append(f"\n\nNFL PROP PICKS:")
        email_content.append("-" * 30)
        email_content.append(nfl_props_tweet)

    # Add NFL referee reports
    print(f"\n--- Processing NFL Referee Report - Totals ---")
    nfl_referee_totals_tweet = create_referee_tweet()
    if nfl_referee_totals_tweet:
        email_content.append(f"\n\nNFL REFEREE REPORT - TOTALS:")
        email_content.append("-" * 30)
        email_content.append(nfl_referee_totals_tweet)

    print(f"\n--- Processing NFL Referee Report - Spreads ---")
    nfl_referee_spreads_tweet = create_referee_spread_tweet()
    if nfl_referee_spreads_tweet:
        email_content.append(f"\n\nNFL REFEREE REPORT - SPREADS:")
        email_content.append("-" * 30)
        email_content.append(nfl_referee_spreads_tweet)

    print(f"\n--- Processing NFL Referee Report - Moneylines ---")
    nfl_referee_ml_tweet = create_referee_moneyline_tweet()
    if nfl_referee_ml_tweet:
        email_content.append(f"\n\nNFL REFEREE REPORT - MONEYLINES:")
        email_content.append("-" * 30)
        email_content.append(nfl_referee_ml_tweet)

    # Send email if we have content
    if len(email_content) > 2:  # More than just header
        email_body = '\n'.join(email_content)
        send_email(f"Daily Betting Analysis - {datetime.now().strftime('%m/%d/%Y')}", email_body)
    else:
        print("⚠️ No qualifying content found to email")

    print(f"\n{'='*50}")
    print(f"✅ Analysis completed")
    print(f"{'='*50}")

if __name__ == "__main__":
    print("📧 Running Betting Analysis Email Bot")
    run_betting_analysis()
    print("✅ Completed - exiting")
