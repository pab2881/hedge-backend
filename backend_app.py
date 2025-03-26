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

SPORTS = [
    "soccer_epl",
    "soccer_uefa_champs_league",
    "basketball_nba",
    "tennis_atp_us_open",
    "mma_mixed_martial_arts",
    "cricket_international_test"
]

BOOKMAKER_PRIORITY = ["Bet365", "Paddy Power", "Bet Victor", "888sport", "Betway", "BoyleSports"]

API_KEY = "d9e11b9c538cb889fe1d99694728fe64"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities(min_profit: float = Query(-10.0)):
    opportunities = []

    async with httpx.AsyncClient() as client:
        for sport in SPORTS:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
                params = {
                    "apiKey": API_KEY,
                    "regions": "uk",
                    "markets": "h2h",
                    "oddsFormat": "decimal"
                }
                response = await client.get(url, params=params)
                if not response.status_code == 200:
                    print(f"API error for {sport}: {response.status_code} - {response.text}")
                    continue
                matches = response.json()

                for match in matches:
                    home = match.get("home_team")
                    away = match.get("away_team")
                    bookmakers = match.get("bookmakers", [])
                    if not (home and away and bookmakers):
                        print(f"Skipping {sport} match: missing data - {match}")
                        continue

                    best_odds = {}
                    for bookmaker in bookmakers:
                        key = bookmaker["key"].replace("_", " ").title()
                        if key not in BOOKMAKER_PRIORITY:
                            continue
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
                            estimated_profit = round(win_return - (stake1 + stake2), 2)  # Fixed profit calc

                            opportunities.append({
                                "sport": sport,  # Added for frontend grouping
                                "team1": team1,
                                "team2": team2,
                                "odds1": odds1,
                                "odds2": odds2,
                                "platform1": best_odds[team1]["bookmaker"],
                                "platform2": best_odds[team2]["bookmaker"],
                                "stake1": stake1,
                                "stake2": stake2,
                                "estimatedProfit": estimated_profit,
                                "profitPercentage": profit_margin  # Added for filtering
                            })

            except Exception as e:
                print(f"Error fetching {sport}: {str(e)}")
                continue

    # Fallback test match
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
            "profitPercentage": 2.38
        })

    return opportunities

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_app:app", host="0.0.0.0", port=10000)
