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

# Full sports list: UK/Euro football, tennis, darts, golf, MMA, boxing, baseball, basketball
SPORTS = [
    # UK Football
    "soccer_epl", "soccer_england_championship", "soccer_england_league1", "soccer_england_league2", "soccer_fa_cup",
    # European Football
    "soccer_uefa_champs_league", "soccer_uefa_europa_league", "soccer_spain_la_liga", "soccer_italy_serie_a",
    "soccer_germany_bundesliga", "soccer_france_ligue_one", "soccer_portugal_primeira_liga", "soccer_netherlands_eredivisie",
    # Basketball
    "basketball_nba", "basketball_wnba", "basketball_euroleague", "basketball_ncaab",
    # Baseball
    "baseball_mlb", "baseball_kbo", "baseball_npb",
    # Tennis
    "tennis_atp_us_open", "tennis_wta_us_open", "tennis_atp_french_open", "tennis_wta_french_open",
    "tennis_atp_wimbledon", "tennis_wta_wimbledon",
    # MMA & Boxing
    "mma_mixed_martial_arts", "boxing",
    # Golf
    "golf_pga_championship", "golf_masters", "golf_us_open",
    # Darts
    "darts_pdc_world_championship", "darts_premier_league"
]

API_KEY = "d9e11b9c538cb889fe1d99694728fe64"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities(min_profit: float = Query(-10.0), sport: str = Query(None)):
    opportunities = []

    async with httpx.AsyncClient() as client:
        sports_to_fetch = [sport] if sport and sport in SPORTS else SPORTS
        for sport_key in sports_to_fetch:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
                params = {
                    "apiKey": API_KEY,
                    "regions": "uk",
                    "markets": "h2h",
                    "oddsFormat": "decimal"
                }
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    print(f"API error for {sport_key}: {response.status_code} - {response.text}")
                    continue
                matches = response.json()
                print(f"Fetched {len(matches)} matches for {sport_key}")

                for match in matches:
                    home = match.get("home_team")
                    away = match.get("away_team")
                    bookmakers = match.get("bookmakers", [])
                    if not (home and away and bookmakers):
                        print(f"Skipping {sport_key} match: missing data - {match}")
                        continue

                    # Check if match is live
                    is_live = match.get("inplay", False) or match.get("live", False)
                    print(f"Match {home} vs {away} - Live: {is_live}")

                    best_odds = {}
                    for bookmaker in bookmakers:
                        key = bookmaker["key"].replace("_", " ").title()
                        for market in bookmaker.get("markets", []):
                            if market["key"] != "h2h":
                                continue
                            for outcome in market.get("outcomes", []):
                                team = outcome["name"]
                                odds = outcome["price"]
                                if team not in best_odds or odds > best_odds[team]["odds"]:
                                    best_odds[team] = {
                                        "bookmaker": key,
                                        "odds": odds
                                    }

                    if len(best_odds) == 2:  # Two-outcome logic
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
                                "isLive": is_live  # Flag for frontend
                            })

            except Exception as e:
                print(f"Error fetching {sport_key}: {str(e)}")
                continue

    # Fallback test match if no data
    if not opportunities:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_app:app", host="0.0.0.0", port=10000)
