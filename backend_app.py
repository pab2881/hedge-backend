from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from fractions import Fraction

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SPORTS = {
    "soccer_epl": {"league": 39, "season": "2024"}  # EPL, current season
}

API_FOOTBALL_KEY = "533408ae1amshb7e0315d7d0de43p1f3964jsn330773ba97e5"  # Your key

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities(min_profit: float = Query(-10.0), sport: str = Query(None)):
    opportunities = []

    async with httpx.AsyncClient() as client:
        sports_to_fetch = [sport] if sport and sport in SPORTS else SPORTS.keys()
        
        for sport_key in sports_to_fetch:
            try:
                league_id = SPORTS[sport_key]["league"]
                season = SPORTS[sport_key]["season"]
                url = "https://api-football-v1.p.rapidapi.com/v3/odds"
                headers = {
                    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
                    "X-RapidAPI-Key": API_FOOTBALL_KEY
                }
                params = {
                    "league": league_id,
                    "season": season,
                    "bookmaker": "8"  # Bet365
                }
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 429:
                    print(f"API-Football rate limit hit for {sport_key}: {response.text}")
                    break
                if response.status_code != 200:
                    print(f"API-Football error for {sport_key}: {response.status_code} - {response.text}")
                    continue
                data = response.json().get("response", [])
                print(f"API-Football fetched {len(data)} matches for {sport_key}: {data[:2]}")
                opportunities.extend(process_matches(data, sport_key, min_profit))
                await asyncio.sleep(1)  # 1s delay - 100/day limit
            except Exception as e:
                print(f"API-Football fetch error for {sport_key}: {str(e)}")

    if not opportunities:
        print("No opportunities found - using fallback")
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

def process_matches(matches, sport_key, min_profit):
    opportunities = []
    for match in matches:
        home = match.get("fixture", {}).get("teams", {}).get("home", {}).get("name")
        away = match.get("fixture", {}).get("teams", {}).get("away", {}).get("name")
        bookmakers = match.get("bookmakers", [])
        if not (home and away and bookmakers):
            print(f"Skipping {sport_key} match - missing data: {match}")
            continue

        best_odds = {}
        for bookmaker in bookmakers:
            if bookmaker.get("bookmaker", {}).get("id") != 8:  # Bet365
                continue
            for bet in bookmaker.get("bets", []):
                if bet.get("name") != "Match Winner":
                    continue
                for outcome in bet.get("values", []):
                    team = outcome.get("value")
                    odds = float(outcome.get("odd", 0))
                    if team and odds and (team not in best_odds or odds > best_odds[team]["odds"]):
                        best_odds[team] = {"bookmaker": "Bet365", "odds": odds}

        if len(best_odds) >= 2:
            team1, team2 = list(best_odds.keys())[:2]  # Home vs Away
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
                    "isLive": False
                })
    return opportunities

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_app:app", host="0.0.0.0", port=10000)
