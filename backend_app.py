# backend_app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI()

# Allow frontend on localhost and Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://hedge-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ODDS_API_KEY = "bedeb6677cd194bfc4c8d12d3898a594"

@app.get("/api/hedge-opportunities")
async def get_hedge_opportunities():
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "uk",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            return {"error": "Failed to fetch odds"}

        raw_data = response.json()
        # 🔧 Transform this data into your format here (simplified):
        hedge_opportunities = []

        for match in raw_data:
            if len(match["bookmakers"]) >= 2:
                home = match["bookmakers"][0]["markets"][0]["outcomes"][0]
                away = match["bookmakers"][1]["markets"][0]["outcomes"][1]

                hedge_opportunities.append({
                    "match": match["home_team"] + " vs " + match["away_team"],
                    "commence_time": match["commence_time"],
                    "bets": [
                        {
                            "bookmaker": match["bookmakers"][0]["title"],
                            "outcome": home["name"],
                            "odds": home["price"],
                        },
                        {
                            "bookmaker": match["bookmakers"][1]["title"],
                            "outcome": away["name"],
                            "odds": away["price"],
                        },
                    ]
                })

        return hedge_opportunities

