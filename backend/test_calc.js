const positions = [
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
  }
];

fetch('http://127.0.0.1:8000/api/portfolio/metrics/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ positions })
}).then(r => r.json()).then(console.log).catch(console.error);
