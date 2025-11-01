# config.py

# Define la ruta de salida para los CSV generados
OUTPUT_DIRECTORY = "output/"

# Define las columnas/métricas de interés.
# Estas deben coincidir con las claves que devuelve yfinance en ticker.info
#
# Ticker -> (Se añade automáticamente, no es de yfinance.info)
# TTM    -> Usaremos 'trailingEps' (Earnings Per Share - Trailing Twelve Months)
# PE     -> Usaremos 'trailingPE' (Price-to-Earnings ratio TTM)
# ROE    -> Usaremos 'returnOnEquity'
METRICS_OF_INTEREST = {
    'symbol': 'Ticker',          # 'symbol' es la clave en .info
    'trailingEps': 'EPS (TTM)',
    'trailingPE': 'PE (TTM)',
    'returnOnEquity': 'ROE'
}

# Define el nombre de las columnas en el CSV final
CSV_COLUMN_NAMES = [
    'Ticker',
    'EPS (TTM)',
    'PE (TTM)',
    'ROE'
]