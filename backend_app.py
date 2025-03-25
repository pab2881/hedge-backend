from fastapi import FastAPI
import httpx
from decimal import Decimal, getcontext

getcontext().prec = 6

app = FastAPI()

BOOKMAKER_PRIORITY = {
    "Bet365": 1,
    "Paddy Power": 2,
    "Bet Victor": 3,
    "Betway": 4,
    "888sport": 5,
    "BoyleSports": 6,
}

@app.get("/api/hedge-opportunities")
async def hedge_opportunities():
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
    params = {
        "apiKey": "bedeb6677cd194bfc4c8d12d3898a594",
        "regions": "uk",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        return []

    matches = response.json()
    opportunities = []

    for match in matches:
        outcomes = {}
        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    name = outcome["name"]
                    if name not in outcomes or outcome["price"] > outcomes[name]["price"]:
                        outcomes[name] = {
                            "price": outcome["price"],
                            "bookmaker": bookmaker["title"]
                        }

        if len(outcomes) == 2:
            teams = list(outcomes.keys())
            odds1 = Decimal(outcomes[teams[0]]["price"])
            odds2 = Decimal(outcomes[teams[1]]["price"])

            # Convert odds to implied probabilities
            implied_prob_1 = Decimal(1) / odds1
            implied_prob_2 = Decimal(1) / odds2
            total_prob = implied_prob_1 + implied_prob_2
            margin = float((1 - total_prob) * 100)

            # Hedge logic: target return = £200
            target_return = Decimal(200)
            stake1 = round(target_return / odds1, 2)
            stake2 = round(target_return / odds2, 2)

            opportunity = {
                "match": match["home_team"] + " vs " + match["away_team"],
                "commence_time": match["commence_time"],
                "impliedProbability": float(total_prob * 100),
                "profitMargin": round(margin, 2),
                "bets": [
                    {
                        "bookmaker": outcomes[teams[0]]["bookmaker"],
                        "outcome": teams[0],
                        "odds": float(odds1),
                        "fractional_odds": to_fractional(odds1),
                        "stake": float(stake1),
                        "win_return": float(target_return)
                    },
                    {
                        "bookmaker": outcomes[teams[1]]["bookmaker"],
                        "outcome": teams[1],
                        "odds": float(odds2),
                        "fractional_odds": to_fractional(odds2),
                        "stake": float(stake2),
                        "win_return": float(target_return)
                    }
                ]
            }

            opportunities.append(opportunity)

    return opportunities


def to_fractional(decimal_odds):
    """Convert decimal odds to fractional string"""
    decimal_odds = float(decimal_odds)
    if decimal_odds < 1.01:
        return "N/A"
    numerator = round((decimal_odds - 1) * 100)
    denominator = 100
    while numerator % 5 == 0 and denominator % 5 == 0:
        numerator //= 5
        denominator //= 5
    return f"{numerator}/{denominator}"
