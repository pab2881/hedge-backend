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

# Sports mapped to AllSportsAPI tournament/season IDs (examples - expand as needed)
SPORTS = {
    "soccer_epl": {"tournament": 8, "season": 61643},  # Premier League 2024/25
    "soccer_spain_la_liga": {"tournament": 87, "season": 61642},  # La Liga
    "soccer_italy_serie_a": {"tournament": 94, "season": 61641},  # Serie A
    "basketball_nba": {"tournament": 132, "season": 61640},  # NBA (season ID guessed)
    "baseball_mlb": {"tournament": 141, "season": 61639},  # MLB (guessed)
    "tennis_atp_us_open": {"tournament": 188, "season": 61638},  # ATP US Open (guessed)
    # Add more from AllSportsAPI docs
}

ALLSPORTS_API_KEY = "533408ae1amshb7e0315d7d0de43p1f3964jsn330773ba97e5"  # Your RapidAPI key

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities(min_profit: float = Query(-10.0), sport: str = Query(None)):
    opportunities = []

    async with httpx.AsyncClient() as client:
        sports_to_fetch = [sport] if sport and sport in SPORTS else SPORTS.keys()
        
        for sport_key in sports_to_fetch:
            try:
                tournament_id = SPORTS[sport_key]["tournament"]
                season_id = SPORTS[sport_key]["season"]
                url = f"https://allsportsapi2.p.rapidapi.com/api/tournament/{tournament_id}/season/{season_id}/odds/pre"
                headers = {
                    "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com",
                    "X-RapidAPI-Key": ALLSPORTS_API_KEY
                }
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    print(f"AllSportsAPI error for {sport_key}: {response.status_code} - {response.text}")
                    continue
                matches = response.json().get("odds", [])
                print(f"AllSportsAPI fetched {len(matches)} matches for {sport_key}")
                opportunities.extend(process_matches(matches, sport_key, min_profit))
            except Exception as e:
                print(f"AllSportsAPI fetch error for {sport_key}: {str(e)}")

    # Fallback test match
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
        home = match.get("homeTeam", {}).get("name")
        away = match.get("awayTeam", {}).get("name")
        markets = match.get("markets", [])
        if not (home and away and markets):
            continue

        best_odds = {}
        for market in markets:
            if market.get("name") != "Match Winner":  # Assuming h2h equivalent
                continue
            for outcome in market.get("selections", []):
                team = outcome.get("name")
                odds = float(outcome.get("odds", 0))
                if team and odds and (team not in best_odds or odds > best_odds[team]["odds"]):
                    best_odds[team] = {"bookmaker": "AllSportsAPI", "odds": odds}

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
                    "isLive": False  # Pre-match odds for now
                })
    return opportunities

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_app:app", host="0.0.0.0", port=10000)
