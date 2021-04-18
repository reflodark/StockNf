# StockNf
Simple python stock email notifier

```json config.json example
{
  "host": "yahoo-finance-low-latency.p.rapidapi.com",
  "api_key": "1234oiu1345oi123aslrktj2340958lkj234sdflkjdfklj999",
  "interval": 60,
  "email": "max@example.com",
  "notifications": [
    { "symbol": "USDEUR=X", "price": 100, "percentage": 10 },
    { "symbol": "JNJ", "price": 100, "percentage": 10 }
  ]
}