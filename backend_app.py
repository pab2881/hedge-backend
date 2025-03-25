from fastapi import FastAPI
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fractions import Fraction

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Settings
API_KEY = "bedeb6677cd194bfc4c8d12d3898a594"
SPORTS = ["soccer_epl", "soccer_uefa_champs_league", "soccer_england_league1"]
REGIONS = "uk"
MARKETS = "h2h"
BOOKMAKER_PRIORITY = ["Bet365", "Paddy Power", "Bet Victor", "888sport", "Betway", "BoyleSports"]

def to_fraction(decimal_odds):
    return str(Fraction(decimal_odds - 1).limit_denominator()) if decimal_odds else "-"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities():
    opportunities = []
    shown_non_profitable = False

    async with httpx.AsyncClient() as client:
        for sport in SPORTS:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
            params = {
                "apiKey": API_KEY,
                "regions": REGIONS,
                "markets": MARKETS,
                "oddsFormat": "decimal"
            }

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                matches = response.json()
            except Exception as e:
                print(f"Error fetching data for {sport}: {e}")
                continue

            for match in matches:
                bookmakers = match.get("bookmakers", [])
                best_odds = {}

                for bookmaker in bookmakers:
                    name = bookmaker["title"]
                    if name not in BOOKMAKER_PRIORITY:
                        continue

                    for market in bookmaker.get("markets", []):
                        if market["key"] != "h2h":
                            continue
                        for outcome in market.get("outcomes", []):
                            team = outcome["name"]
                            price = outcome["price"]
                            if team not in best_odds or price > best_odds[team]["price"]:
                                best_odds[team] = {
                                    "bookmaker": name,
                                    "price": price
                                }

                if len(best_odds) == 2:
                    teams = list(best_odds.keys())
                    odds_1 = best_odds[teams[0]]["price"]
                    odds_2 = best_odds[teams[1]]["price"]

                    implied_prob = (1 / odds_1) + (1 / odds_2)
                    profit_margin = round((1 - implied_prob) * 100, 2)

                    show_bet = profit_margin > 0 or (not shown_non_profitable and profit_margin > -2)
                    if not show_bet:
                        continue

                    stake_1 = round(200 / odds_1, 2)
                    stake_2 = round(200 / odds_2, 2)
                    win_return = round(stake_1 * odds_1, 2)

                    bets = [
                        {
                            "bookmaker": best_odds[teams[0]]["bookmaker"],
                            "outcome": teams[0],
                            "odds": odds_1,
                            "fractional_odds": to_fraction(odds_1),
                            "stake": stake_1,
                            "win_return": win_return
                        },
                        {
                            "bookmaker": best_odds[teams[1]]["bookmaker"],
                            "outcome": teams[1],
                            "odds": odds_2,
                            "fractional_odds": to_fraction(odds_2),
                            "stake": stake_2,
                            "win_return": win_return
                        }
                    ]

                    opportunities.append({
                        "match": f"{match['home_team']} vs {match['away_team']}",
                        "commence_time": match["commence_time"],
                        "impliedProbability": round(implied_prob * 100, 2),
                        "profitMargin": profit_margin,
                        "bets": bets
                    })

                    if profit_margin <= 0:
                        shown_non_profitable = True

    return opportunities

