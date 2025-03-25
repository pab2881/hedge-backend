from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fractions import Fraction
from typing import List
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOOKMAKER_PRIORITY = ["Bet365", "Paddy Power", "Bet Victor", "888sport", "Betway", "BoyleSports"]
API_KEY = "bedeb6677cd194bfc4c8d12d3898a594"
API_URL = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds?apiKey={API_KEY}&regions=uk&markets=h2h&oddsFormat=decimal"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_URL)
            data = response.json()

        opportunities = []

        for match in data:
            match_name = match.get("home_team", "") + " vs " + match.get("away_team", "")
            commence_time = match.get("commence_time", "")

            bookmakers = match.get("bookmakers", [])
            best_odds = {}

            for bookmaker in bookmakers:
                key = bookmaker["key"].replace("_", " ").title()
                if key not in BOOKMAKER_PRIORITY:
                    continue

                for market in bookmaker.get("markets", []):
                    if market["key"] == "h2h":
                        for i, outcome in enumerate(market["outcomes"]):
                            team = outcome["name"]
                            odds = outcome["price"]

                            if team not in best_odds or odds > best_odds[team]["odds"]:
                                best_odds[team] = {
                                    "bookmaker": key,
                                    "odds": odds
                                }

            if len(best_odds) == 2:
                teams = list(best_odds.keys())
                team1, team2 = teams[0], teams[1]
                odds1 = best_odds[team1]["odds"]
                odds2 = best_odds[team2]["odds"]

                implied_prob = round((1 / odds1 + 1 / odds2) * 100, 2)
                profit_margin = round(100 - implied_prob, 2)

                stake1 = 100
                stake2 = round((stake1 * odds1) / odds2, 2)
                win_return = round(stake1 * odds1, 2)

                def to_fraction(decimal_odds):
                    return str(Fraction(decimal_odds - 1).limit_denominator()) if decimal_odds else "-"

                bet_details = [
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

                opportunities.append({
                    "match": match_name,
                    "commence_time": commence_time,
                    "impliedProbability": implied_prob,
                    "profitMargin": profit_margin,
                    "bets": bet_details
                })

        return opportunities

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

