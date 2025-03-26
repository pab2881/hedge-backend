from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fractions import Fraction

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Valid sports keys
SPORTS = [
    "soccer_epl",
    "soccer_uefa_champs_league"
]

BOOKMAKER_PRIORITY = ["Bet365", "Paddy Power", "Bet Victor", "888sport", "Betway", "BoyleSports"]

# Working Odds API key
API_KEY = "d9e11b9c538cb889fe1d99694728fe64"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities():
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
                response.raise_for_status()
                matches = response.json()

                for match in matches:
                    home = match.get("home_team")
                    away = match.get("away_team")
                    bookmakers = match.get("bookmakers", [])
                    best_odds = {}

                    # Find the best odds for each team from prioritized bookmakers
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
                        # Extract team names and their odds
                        team_names = list(best_odds.keys())
                        team1, team2 = team_names[0], team_names[1]
                        odds1 = best_odds[team1]["odds"]
                        odds2 = best_odds[team2]["odds"]

                        # Calculate implied probability and profit margin
                        implied_prob = round((1 / odds1 + 1 / odds2) * 100, 2)
                        profit_margin = round(100 - implied_prob, 2)

                        # Using a relaxed filter for testing (show bets with margin > -10%)
                        if profit_margin > -10:
                            stake1 = 100  # base stake for team1
                            stake2 = round((stake1 * odds1) / odds2, 2)  # calculated stake for team2
                            win_return = round(stake1 * odds1, 2)
                            estimated_profit = round(win_return - stake1, 2)

                            opportunities.append({
                                "team1": team1,
                                "team2": team2,
                                "odds1": odds1,
                                "odds2": odds2,
                                "platform1": best_odds[team1]["bookmaker"],
                                "platform2": best_odds[team2]["bookmaker"],
                                "stake1": stake1,
                                "stake2": stake2,
                                "estimatedProfit": estimated_profit
                            })

            except Exception as e:
                print(f"Error fetching {sport}: {e}")

    # Fallback opportunity for debugging if none are found
    if not opportunities:
        opportunities.append({
            "team1": "Test FC",
            "team2": "Debug United",
            "odds1": 2.0,
            "odds2": 2.1,
            "platform1": "Bet365",
            "platform2": "Paddy Power",
            "stake1": 100,
            "stake2": 95.24,
            "estimatedProfit": 200 - 100  # assuming win_return is 200
        })

    return opportunities

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("backend_app:app", host="0.0.0.0", port=10000)

