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

fetch('http://127.0.0.1:8000/api/portfolio/dividends', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ positions })
}).then(res => console.log(res.status)).catch(console.error);
