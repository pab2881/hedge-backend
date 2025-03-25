from fastapi import FastAPI
import httpx
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from fractions import Fraction

app = FastAPI()

# Enable CORS so frontend can access the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
API_KEY = "bedeb6677cd194bfc4c8d12d3898a594"
SPORT = "soccer_epl"
REGIONS = "uk"
MARKETS = "h2h"
ODDS_API_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities():
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": "decimal"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(ODDS_API_URL, params=params)
        response.raise_for_status()
        matches = response.json()

    opportunities = []

    for match in matches:
        if not match.get("bookmakers"):
            continue

        best_odds = {}
        for bookmaker in match["bookmakers"]:
            for market in bookmaker.get("markets", []):
                if market["key"] != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    team = outcome["name"]
                    price = outcome["price"]
                    if team not in best_odds or price > best_odds[team]["price"]:
                        best_odds[team] = {
                            "bookmaker": bookmaker["title"],
                            "price": price
                        }

        if len(best_odds) == 2:
            teams = list(best_odds.keys())
            odds_1 = best_odds[teams[0]]["price"]
            odds_2 = best_odds[teams[1]]["price"]

            implied_prob = (1 / odds_1 + 1 / odds_2)
            profit_margin = round((1 - implied_prob) * 100, 2)

            if profit_margin > 0:
                total_return = 200  # Fixed total return target
                stake_1 = round(total_return / odds_1, 2)
                stake_2 = round(total_return / odds_2, 2)

                bets = [
                    {
                        "bookmaker": best_odds[teams[0]]["bookmaker"],
                        "outcome": teams[0],
                        "odds": odds_1,
                        "fractional_odds": str(Fraction(odds_1 - 1).limit_denominator(100)),
                        "stake": stake_1,
                        "win_return": round(stake_1 * odds_1, 2),
                    },
                    {
                        "bookmaker": best_odds[teams[1]]["bookmaker"],
                        "outcome": teams[1],
                        "odds": odds_2,
                        "fractional_odds": str(Fraction(odds_2 - 1).limit_denominator(100)),
                        "stake": stake_2,
                        "win_return": round(stake_2 * odds_2, 2),
                    },
                ]

                opportunities.append({
                    "match": match["home_team"] + " vs " + match["away_team"],
                    "commence_time": match["commence_time"],
                    "impliedProbability": round(implied_prob * 100, 2),
                    "profitMargin": profit_margin,
                    "bets": bets
                })

    return opportunities

