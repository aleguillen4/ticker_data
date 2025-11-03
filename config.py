# config.py

# Directorio de salida (sin cambios)
OUTPUT_DIRECTORY = "output/"

import datetime

# Nombres de las filas que queremos en el CSV final
CSV_ROW_NAMES = [
    # Representative values
    'marketCap',
    'beta',
    'peRatio',
    'forwardDividendRate',
    'EPS',
    '52WeekRange',
    'trailingPE',
    'forwardPE',
    'profitMargin',
    'dividend_and_split',
    'payoutRatio',
    'ROE',
    # Financials subsection
    'totalRevenue',
    'costOfRevenue',
    'operatingExpense',
    'netIncome',
    # Balance sheets subsection
    'cash cash equivalence',
    'total assets',
    'total liabilities',
    'working capital',
    'invested capital',
    'total debts',
    'ordinary shared number',
    'net tangible assets'
]

# Años a extraer (desde 2021 hasta el año actual)
START_YEAR = 2021
YEARS_TO_EXTRACT = list(range(START_YEAR, datetime.datetime.now().year + 1))