# Crypto Engine Validation

Validation data was reset on 2026-08-22 after correcting an outcome-calculation bug. The previous records evaluated candles from before the alert timestamp and were not valid accuracy measurements.

A fresh validation run will populate this report using only completed 1-minute candles formed after each alert.
