from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fractions import Fraction

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sports list (split across APIs)
SPORTS = {
    "sportmonks": ["soccer_scotland_premiership", "darts_pdc_world_championship", "golf_pga_championship"],
    "api_football": ["soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a", "soccer_germany_bundesliga", "soccer_france_ligue_one"],
    "odds_api": ["basketball_nba", "baseball_mlb", "tennis_atp_us_open", "mma_mixed_martial_arts", "boxing"]
}

# API Keys (replace with yours after signup)
ODDS_API_KEY = "d9e11b9c538cb889fe1d99694728fe64"
SPORTMONKS_API_KEY = "YOUR_SPORTMONKS_KEY"  # Get from sportmonks.com
API_FOOTBALL_KEY = "YOUR_API_FOOTBALL_KEY"  # Get from rapidapi.com

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities(min_profit: float = Query(-10.0), sport: str = Query(None)):
    opportunities = []

    async with httpx.AsyncClient() as client:
        sports_to_fetch = [sport] if sport and any(sport in v for v in SPORTS.values()) else sum(SPORTS.values(), [])

        # Sportmonks fetch
        for sport_key in [s for s in sports_to_fetch if s in SPORTS["sportmonks"]]:
            try:
                url = f"https://api.sportmonks.com/v3/football/fixtures?api_token={SPORTMONKS_API_KEY}&include=odds"
                response = await client.get(url)
                if response.status_code != 200:
                    print(f"Sportmonks error for {sport_key}: {response.status_code} - {response.text}")
                    continue
                data = response.json().get("data", [])
                matches = [{"home_team": m["participants"][0]["name"], "away_team": m["participants"][1]["name"], 
                           "bookmakers": [{"key": "sportmonks", "markets": [{"key": "h2h", "outcomes": m["odds"]}]}]} 
                          for m in data if "odds" in m]
                print(f"Sportmonks fetched {len(matches)} matches for {sport_key}")
                opportunities.extend(process_matches(matches, sport_key, min_profit))
            except Exception as e:
                print(f"Sportmonks fetch error for {sport_key}: {str(e)}")

        # API-Football fetch
        for sport_key in [s for s in sports_to_fetch if s in SPORTS["api_football"]]:
            try:
                url = "https://api-football-v1.p.rapidapi.com/v3/odds"
                headers = {"X-RapidAPI-Key": API_FOOTBALL_KEY, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
                params = {"league": sport_key.split("_")[-1]}  # Simplified - needs league ID mapping
                response = await client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    print(f"API-Football error for {sport_key}: {response.status_code} - {response.text}")
                    continue
                data = response.json().get("response", [])
                matches = [{"home_team": m["fixture"]["teams"]["home"]["name"], "away_team": m["fixture"]["teams"]["away"]["name"],
                           "bookmakers": [{"key": b["bookmaker"]["name"], "markets": [{"key": "h2h", "outcomes": b["bets"][0]["values"]}]} 
                                          for b in m["bookmakers"]]} for m in data]
                print(f"API-Football fetched {len(matches)} matches for {sport_key}")
                opportunities.extend(process_matches(matches, sport_key, min_profit))
            except Exception as e:
                print(f"API-Football fetch error for {sport_key}: {str(e)}")

        # Odds API (sparingly - quota hit)
        for sport_key in [s for s in sports_to_fetch if s in SPORTS["odds_api"]]:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
                params = {"apiKey": ODDS_API_KEY, "regions": "uk", "markets": "h2h", "oddsFormat": "decimal"}
                response = await client.get(url, params=params)
                if response.status_code == 429:
                    print(f"Odds API quota exceeded for {sport_key}: {response.text}")
                    break
                if response.status_code != 200:
                    print(f"Odds API error for {sport_key}: {response.status_code} - {response.text}")
                    continue
                matches = response.json()
                print(f"Odds API fetched {len(matches)} matches for {sport_key}, Credits left: {response.headers.get('x-requests-remaining', 'unknown')}")
                opportunities.extend(process_matches(matches, sport_key, min_profit))
            except Exception as e:
                print(f"Odds API fetch error for {sport_key}: {str(e)}")

    # Fallback test match
    if not opportunities:
        print("No opportunities found - using fallback")
        opportunities.append({
            "sport": "test",
            "team1": "Test FC",
            "team2": "Debug United",
            "odds1": 2.0,
            "odds2": 2.1,
            "platform1": "Bet365",
            "platform2": "Paddy Power",
            "stake1": 100,
            "stake2": 95.24,
            "estimatedProfit": 100,
            "profitPercentage": 2.38,
            "isLive": False
        })

    return opportunities

def process_matches(matches, sport_key, min_profit):
    opportunities = []
    for match in matches:
        home = match.get("home_team")
        away = match.get("away_team")
        bookmakers = match.get("bookmakers", [])
        if not (home and away and bookmakers):
            continue

        best_odds = {}
        for bookmaker in bookmakers:
            key = bookmaker["key"]
            for market in bookmaker.get("markets", []):
                if market["key"] != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    team = outcome["name"] if "name" in outcome else outcome.get("value", {}).get("name")
                    odds = outcome["price"] if "price" in outcome else float(outcome.get("value", {}).get("odd", 0))
                    if team and odds and (team not in best_odds or odds > best_odds[team]["odds"]):
                        best_odds[team] = {"bookmaker": key, "odds": odds}

        if len(best_odds) == 2:
            team1, team2 = list(best_odds.keys())
            odds1 = best_odds[team1]["odds"]
            odds2 = best_odds[team2]["odds"]

            implied_prob = round((1 / odds1 + 1 / odds2) * 100, 2)
            profit_margin = round(100 - implied_prob, 2)

            if profit_margin >= min_profit:
                stake1 = 100
                stake2 = round((stake1 * odds1) / odds2, 2)
                win_return = round(stake1 * odds1, 2)
                estimated_profit = round(win_return - (stake1 + stake2), 2)

                opportunities.append({
                    "sport": sport_key,
                    "team1": team1,
                    "team2": team2,
                    "odds1": odds1,
                    "odds2": odds2,
                    "platform1": best_odds[team1]["bookmaker"],
                    "platform2": best_odds[team2]["bookmaker"],
                    "stake1": stake1,
                    "stake2": stake2,
                    "estimatedProfit": estimated_profit,
                    "profitPercentage": profit_margin,
                    "isLive": False  # Simplified - adjust per API if available
                })
    return opportunities

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_app:app", host="0.0.0.0", port=10000)
