import requests

positions = [
  {
    "Wertpapier": "Apple Inc.",
    "Ticker": "AAPL",
    "St_Nom": 10,
    "Kaufwert": 1500,
    "Avg_Kaufkurs": 150,
    "Aktueller_Kurs": None,
    "Akt_Wert": 1700,
    "Gewinn_Verlust": 200,
    "Performance": 13.33
  }
]

res = requests.post('http://127.0.0.1:8000/api/portfolio/dividends', json={"positions": positions})
print("Status:", res.status_code)
if res.status_code == 422:
    print(res.json())
