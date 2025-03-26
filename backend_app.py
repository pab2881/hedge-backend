from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fractions import Fraction

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Valid sports only
SPORTS = [
    "soccer_epl",
    "soccer_uefa_champs_league"
]

BOOKMAKER_PRIORITY = ["Bet365", "Paddy Power", "Bet Victor", "888sport", "Betway", "BoyleSports"]

# ✅ Working Odds API key
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
                    match_name = f"{home} vs {away}"
                    commence_time = match.get("commence_time", "")
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

                        if profit_margin > -2:
                            stake1 = 100
                            stake2 = round((stake1 * odds1) / odds2, 2)
                            win_return = round(stake1 * odds1, 2)

                            def to_fraction(odds):
                                return str(Fraction(odds - 1).limit_denominator())

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

                            opportunities.append({
                                "match": match_name,
                                "commence_time": commence_time,
                                "impliedProbability": implied_prob,
                                "profitMargin": profit_margin,
                                "bets": bets
                            })

            except Exception as e:
                print(f"Error fetching {sport}: {e}")

    # ✅ Fallback test bet
    if not opportunities:
        opportunities.append({
            "match": "Test FC vs Debug United",
            "commence_time": "2025-04-01T19:00:00Z",
            "impliedProbability": 98.0,
            "profitMargin": 2.0,
            "bets": [
                {
                    "bookmaker": "Bet365",
                    "outcome": "Test FC",
                    "odds": 2.0,
                    "fractional_odds": "1/1",
                    "stake": 100,
                    "win_return": 200
                },
                {
                    "bookmaker": "Paddy Power",
                    "outcome": "Debug United",
                    "odds": 2.1,
                    "fractional_odds": "11/10",
                    "stake": 95.24,
                    "win_return": 200
                }
            ]
        })

    return opportunities

