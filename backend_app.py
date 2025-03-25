from fastapi import FastAPI
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fractions import Fraction
from datetime import datetime

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOOKMAKER_PRIORITY = ["Bet365", "Paddy Power", "Bet Victor", "888sport", "Betway", "BoyleSports"]
API_KEY = "bedeb6677cd194bfc4c8d12d3898a594"
SPORTS = ["soccer_epl", "soccer_champions_league", "soccer_england_championship"]
BASE_URL = "https://api.the-odds-api.com/v4/sports"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities():
    opportunities = []

    for sport in SPORTS:
        url = f"{BASE_URL}/{sport}/odds"
        params = {
            "apiKey": API_KEY,
            "regions": "uk",
            "markets": "h2h",
            "oddsFormat": "decimal"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                matches = response.json()

            for match in matches:
                match_name = f"{match.get('home_team')} vs {match.get('away_team')}"
                commence_time = match.get("commence_time", "")
                bookmakers = match.get("bookmakers", [])
                best_odds = {}

                for bookmaker in bookmakers:
                    key = bookmaker["title"]
                    if key not in BOOKMAKER_PRIORITY:
                        continue

                    for market in bookmaker.get("markets", []):
                        if market["key"] != "h2h":
                            continue
                        for outcome in market["outcomes"]:
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

                    stake1 = 100
                    stake2 = round((stake1 * odds1) / odds2, 2)
                    win_return = round(stake1 * odds1, 2)

                    def to_fraction(decimal_odds):
                        return str(Fraction(decimal_odds - 1).limit_denominator()) if decimal_odds else "-"

                    bets = [
                        {
                            "bookmaker": best_odds[team1]["bookmaker"],
                            "outcome": team1,
                            "odds": odds1,
                            "fractional_odds": to_fraction(odds1),
                            "stake": stake1,
                            "win_return": win_return
                        },
                        {
                            "bookmaker": best_odds[team2]["bookmaker"],
                            "outcome": team2,
                            "odds": odds2,
                            "fractional_odds": to_fraction(odds2),
                            "stake": stake2,
                            "win_return": win_return
                        }
                    ]

                    if profit_margin > 0 or sport == SPORTS[0]:  # show one non-profitable from top sport
                        opportunities.append({
                            "match": match_name,
                            "commence_time": commence_time,
                            "impliedProbability": implied_prob,
                            "profitMargin": profit_margin,
                            "bets": bets
                        })

        except Exception as e:
            print(f"Error fetching data for {sport}: {e}")

    # Always return at least one dummy bet for debugging
    if not opportunities:
        opportunities.append({
            "match": "Debug FC vs Test United",
            "commence_time": datetime.utcnow().isoformat(),
            "impliedProbability": 110.0,
            "profitMargin": -10.0,
            "bets": [
                {
                    "bookmaker": "Test Bookmaker A",
                    "outcome": "Debug FC",
                    "odds": 1.5,
                    "fractional_odds": "1/2",
                    "stake": 100,
                    "win_return": 150
                },
                {
                    "bookmaker": "Test Bookmaker B",
                    "outcome": "Test United",
                    "odds": 3.5,
                    "fractional_odds": "5/2",
                    "stake": 42.86,
                    "win_return": 150
                }
            ]
        })

    return opportunities

