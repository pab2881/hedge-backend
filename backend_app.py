from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BOOKMAKERS = ["bet365", "paddypower", "betvictor", "888sport", "betway", "boylesports"]
API_KEY = "bedeb6677cd194bfc4c8d12d3898a594"
REGION = "uk"
MARKETS = "h2h"
SPORT = "soccer_epl"

def calculate_stakes(odds1, odds2):
    total = 100
    stake1 = round(total / (1 + odds1 / odds2), 2)
    stake2 = round(total - stake1, 2)
    return stake1, stake2

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds?apiKey={API_KEY}&regions={REGION}&markets={MARKETS}&oddsFormat=decimal"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

    opportunities = []

    for match in data:
        bookmakers = match.get("bookmakers", [])
        if len(bookmakers) < 2:
            continue

        best_bets = {}
        for bookmaker in bookmakers:
            if bookmaker["key"] not in BOOKMAKERS:
                continue
            for market in bookmaker["markets"]:
                for outcome in market["outcomes"]:
                    name = outcome["name"]
                    if name not in best_bets or outcome["price"] > best_bets[name]["price"]:
                        best_bets[name] = {
                            "bookmaker": bookmaker["title"],
                            "odds": outcome["price"],
                        }

        if len(best_bets) >= 2:
            bets = list(best_bets.items())[:2]
            odds1 = bets[0][1]["odds"]
            odds2 = bets[1][1]["odds"]
            stake1, stake2 = calculate_stakes(odds1, odds2)
            win_return = round(max(stake1 * odds1, stake2 * odds2), 2)

            opportunities.append({
                "match": match["home_team"] + " vs " + match["away_team"],
                "commence_time": match["commence_time"],
                "bets": [
                    {
                        "bookmaker": bets[0][1]["bookmaker"],
                        "outcome": bets[0][0],
                        "odds": odds1,
                        "stake": stake1,
                        "win_return": round(stake1 * odds1, 2),
                        "fractional_odds": "-"
                    },
                    {
                        "bookmaker": bets[1][1]["bookmaker"],
                        "outcome": bets[1][0],
                        "odds": odds2,
                        "stake": stake2,
                        "win_return": round(stake2 * odds2, 2),
                        "fractional_odds": "-"
                    }
                ]
            })

    return opportunities
