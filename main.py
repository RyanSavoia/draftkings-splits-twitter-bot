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
            
            # Check away team spread (they get + spread)
            away_diff = spread_away_stake - spread_away_bets
            if away_diff >= 30:
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
            if home_diff >= 30:
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
            
            # Check away team moneyline
            away_ml_diff = ml_away_stake - ml_away_bets
            if away_ml_diff >= 30:
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
            if home_ml_diff >= 30:
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
