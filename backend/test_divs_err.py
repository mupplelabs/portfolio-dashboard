import requests

positions = [
  {
    "Wertpapier": "Apple Inc.",
    "Ticker": "AAPL",
    "St_Nom": 10,
    "Kaufwert": 1500,
    "Avg_Kaufkurs": 150,
    "Aktueller_Kurs": 170,
    "Akt_Wert": 1700,
    "Gewinn_Verlust": 200,
    "Performance": 13.33
  },
  {
    "Wertpapier": "Microsoft",
    "Ticker": "MSFT",
    "St_Nom": 5,
    "Kaufwert": 1000,
    "Kaufpreis": 1000,
    "Orderkost": 0,
    "Avg_Kaufkurs": 0,
    "Aktueller_Kurs": 300,
    "Akt_Wert": 1500,
    "Live_Gesamtwert": 1500,
    "Gewinn_Verlust": 0,
    "Performance": 0
  }
]

res = requests.post('http://127.0.0.1:8000/api/portfolio/dividends', json={"positions": positions})
print("Status:", res.status_code)
if res.status_code == 422:
    print(res.json())
