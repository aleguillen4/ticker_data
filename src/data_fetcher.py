# src/data_fetcher.py

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
from config import CSV_ROW_NAMES, YEARS_TO_EXTRACT

def safe_get_value(df, row_name, date):
    """Accede a un valor del DataFrame de forma segura, devolviendo None si la clave o la fila falta."""
    try:
        value = df.loc[row_name, date]
        return value if pd.notna(value) else None
    except Exception:
        return None


def get_value_candidates(df, candidates, date):
    """Intenta múltiples nombres de fila en orden y devuelve el primero válido."""
    for name in candidates:
        val = safe_get_value(df, name, date)
        if val is not None:
            return val
    return None


def _find_label_by_candidates(df, candidates):
    """Busca una etiqueta (índice) en el DataFrame usando coincidencia normalizada.
    Devuelve la etiqueta original si se encuentra, o None.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    # Build a normalized map of existing index labels -> original
    def _norm(s):
        return str(s).strip().lower().replace(' ', '').replace('_', '')

    idx_map = { _norm(idx): idx for idx in df.index }
    # Try exact normalized matches for candidates
    for cand in candidates:
        key = _norm(cand)
        if key in idx_map:
            return idx_map[key]
    # Fallback: try substring match (case-insensitive)
    for cand in candidates:
        low = str(cand).strip().lower()
        for orig in df.index:
            try:
                if low in str(orig).strip().lower():
                    return orig
            except Exception:
                continue
    return None


def get_value_candidates_normalized(df, candidates, date):
    """Like get_value_candidates but matches index labels in a case/format-insensitive way."""
    label = _find_label_by_candidates(df, candidates)
    if label is None:
        return None
    return safe_get_value(df, label, date)


def _col_year(col):
    """Return the year for a column label which may be a Timestamp or a string.
    Returns None if it cannot be determined.
    """
    try:
        return col.year
    except Exception:
        try:
            return pd.to_datetime(col).year
        except Exception:
            return None


def calculate_roe(income_statement, balance_sheet, years):
    """Calcula el Return on Equity (ROE) anualizado."""
    roe_data = {}
    for date in (income_statement.columns if isinstance(income_statement, pd.DataFrame) else []):
        year = _col_year(date)
        if year is None:
            continue
        if year in years:
            net_income = get_value_candidates_normalized(income_statement, ['Net Income', 'NetIncome', 'netIncome'], date)
            total_equity = get_value_candidates_normalized(balance_sheet, ['Total Stockholder Equity', 'TotalStockholderEquity', 'Total Stockholders Equity', 'Total Equity', 'TotalAssets'], date)
            if net_income is None or total_equity is None or total_equity == 0:
                roe_data[year] = None
            else:
                roe_data[year] = net_income / total_equity
    return roe_data


def get_year_end_price_series(price_hist, year):
    """Devuelve el precio de cierre del último día de trading del año especificado."""
    year_end = datetime(year, 12, 31)
    # Ensure timezone compatibility between index and comparison value
    try:
        idx_tz = price_hist.index.tz
        if idx_tz is not None:
            year_end = pd.Timestamp(year_end).tz_localize(idx_tz)
        else:
            year_end = pd.Timestamp(year_end)
    except Exception:
        year_end = pd.Timestamp(year_end)
    hist_until = price_hist[price_hist.index <= year_end]
    if hist_until.empty:
        return None
    return hist_until['Close'].iloc[-1]


def get_annual_fundamentals(ticker_symbol: str) -> pd.DataFrame:
    """
    Obtiene y calcula las métricas solicitadas por año (YEARS_TO_EXTRACT) y el valor 'actual'.
    """
    try:
        logging.info(f"Conectando a Yahoo Finance para {ticker_symbol}...")
        ticker = yf.Ticker(ticker_symbol)
        income_statement = ticker.financials
        balance_sheet = ticker.balance_sheet

        # earnings/income statements por año (para EPS)
        earnings_history = None
        # Prefer income_stmt/financials for per-year rows like 'Basic EPS' or 'Diluted EPS'
        for candidate in ('income_stmt', 'earnings', 'earnings_history', 'quarterly_financials'):
            if hasattr(ticker, candidate):
                try:
                    earnings_history = getattr(ticker, candidate)
                    if isinstance(earnings_history, pd.DataFrame) and not earnings_history.empty:
                        break
                except Exception:
                    earnings_history = None

        current_info = ticker.info or {}
        current_price = current_info.get('regularMarketPrice')
        shares_outstanding = current_info.get('sharesOutstanding')

        # Datos históricos de precios y acciones (incluye 'Dividends' y 'Stock Splits')
        start_year = min(YEARS_TO_EXTRACT)
        hist_start = f"{start_year}-01-01"
        hist_end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        price_hist = ticker.history(start=hist_start, end=hist_end, interval='1d', actions=True)
        # Try to fetch a market benchmark (S&P 500) history for beta calculation
        try:
            sp = yf.Ticker("^GSPC")
            market_hist = sp.history(start=hist_start, end=hist_end, interval='1d')
        except Exception:
            market_hist = None

        if (income_statement is None or income_statement.empty) and (price_hist is None or price_hist.empty):
            logging.error(f"Datos históricos incompletos para {ticker_symbol}.")
            return None

        # Pre-create columns for each requested year plus 'actual' so row assignments work consistently
        cols_order = YEARS_TO_EXTRACT + ['actual']
        result_df = pd.DataFrame(index=CSV_ROW_NAMES, columns=cols_order)

        # --- EPS por año ---
        eps_data = {}
        if isinstance(earnings_history, pd.DataFrame):
            # Some yfinance DataFrames expose EPS as rows with date columns (income_stmt)
            # but others (earnings_history) have different shapes. Detect columns as dates.
            first_col = earnings_history.columns[0] if len(earnings_history.columns) > 0 else None
            if _col_year(first_col) is not None:
                # columns are dates
                for date in earnings_history.columns:
                    year = _col_year(date)
                    if year is None:
                        continue
                    if year in YEARS_TO_EXTRACT:
                        eps = None
                        for cand in ['Basic EPS', 'Diluted EPS', 'EPS', 'Earnings Per Share', 'basicEPS', 'dilutedEPS']:
                            eps = safe_get_value(earnings_history, cand, date)
                            if eps is not None:
                                break
                        eps_data[year] = eps
            else:
                # Try to use ticker.income_stmt or ticker.financials for EPS per year
                income_stmt_df = getattr(ticker, 'income_stmt', income_statement)
                if isinstance(income_stmt_df, pd.DataFrame):
                    for date in income_stmt_df.columns:
                        year = _col_year(date)
                        if year is None:
                            continue
                        if year in YEARS_TO_EXTRACT:
                            eps = None
                            for cand in ['Basic EPS', 'Diluted EPS', 'DilutedEPS', 'BasicEPS']:
                                eps = get_value_candidates(income_stmt_df, [cand], date)
                                if eps is not None:
                                    break
                            eps_data[year] = eps
        eps_data['actual'] = current_info.get('trailingEps')
        # Ensure series contains all expected year keys + 'actual'
        eps_series = pd.Series({**{y: None for y in YEARS_TO_EXTRACT}, **{k: v for k, v in eps_data.items() if k in YEARS_TO_EXTRACT or k == 'actual'}, 'actual': eps_data.get('actual')})
        result_df.loc['EPS'] = eps_series

        # --- Total Revenue y Cost of Revenue por año ---
        total_rev = {}
        cost_rev = {}
        for date in (income_statement.columns if isinstance(income_statement, pd.DataFrame) else []):
            year = _col_year(date)
            if year is None:
                continue
            if year in YEARS_TO_EXTRACT:
                tr = get_value_candidates_normalized(income_statement, ['Total Revenue', 'totalRevenue', 'TotalRevenue'], date)
                cr = get_value_candidates_normalized(income_statement, ['Cost Of Revenue', 'Cost of Revenue', 'costOfRevenue', 'CostOfRevenue'], date)
                total_rev[year] = tr
                cost_rev[year] = cr
        result_df.loc['totalRevenue'] = pd.Series({**{y: None for y in YEARS_TO_EXTRACT}, **total_rev, 'actual': current_info.get('totalRevenue')})
        result_df.loc['costOfRevenue'] = pd.Series({**{y: None for y in YEARS_TO_EXTRACT}, **cost_rev, 'actual': None})

        # --- Operating expense y Net Income por año ---
        operating_exp = {}
        net_income_vals = {}
        for date in (income_statement.columns if isinstance(income_statement, pd.DataFrame) else []):
            year = _col_year(date)
            if year is None:
                continue
            if year in YEARS_TO_EXTRACT:
                op = get_value_candidates_normalized(income_statement, ['Operating Expense', 'Operating Expenses', 'OperatingIncome', 'Operating Income', 'operatingExpense', 'operatingExpenses'], date)
                ni = get_value_candidates_normalized(income_statement, ['Net Income', 'NetIncome', 'netIncome', 'Net Income Applicable To Common Shares', 'NetIncomeLoss'], date)
                operating_exp[year] = op
                net_income_vals[year] = ni
        result_df.loc['operatingExpense'] = pd.Series({**{y: None for y in YEARS_TO_EXTRACT}, **operating_exp, 'actual': current_info.get('operatingMargins')})
        result_df.loc['netIncome'] = pd.Series({**{y: None for y in YEARS_TO_EXTRACT}, **net_income_vals, 'actual': current_info.get('netIncomeToCommon') or current_info.get('netIncome')})

        # --- ROE por año (usa calculate_roe) ---
        roe_data = calculate_roe(income_statement if income_statement is not None else pd.DataFrame(),
                                 balance_sheet if balance_sheet is not None else pd.DataFrame(),
                                 YEARS_TO_EXTRACT)
        roe_data['actual'] = current_info.get('returnOnEquity')
        result_df.loc['ROE'] = pd.Series(roe_data)

        # --- Profit margin por año = netIncome / totalRevenue ---
        profit_data = {}
        for date in (income_statement.columns if isinstance(income_statement, pd.DataFrame) else []):
            year = _col_year(date)
            if year is None:
                continue
            if year in YEARS_TO_EXTRACT:
                ni = get_value_candidates_normalized(income_statement, ['Net Income', 'NetIncome', 'netIncome'], date)
                tr = get_value_candidates_normalized(income_statement, ['Total Revenue', 'totalRevenue', 'TotalRevenue'], date)
                if ni is None or tr is None or tr == 0:
                    profit_data[year] = None
                else:
                    profit_data[year] = ni / tr
        profit_data['actual'] = current_info.get('profitMargins')
        result_df.loc['profitMargin'] = pd.Series(profit_data)

        # --- Dividendos y splits por año (suma de dividendos y lista de splits) ---
        divsplit = {}
        if isinstance(price_hist, pd.DataFrame) and 'Dividends' in price_hist.columns:
            for year in YEARS_TO_EXTRACT:
                mask = price_hist.index.year == year
                if mask.any():
                    total_div = price_hist.loc[mask, 'Dividends'].sum()
                    splits = price_hist.loc[mask, 'Stock Splits']
                    split_events = splits[splits != 0].astype(str).tolist()
                    divsplit[year] = {'dividends': float(total_div) if total_div != 0 else None, 'splits': split_events if split_events else None}
                else:
                    divsplit[year] = None
        last_div = current_info.get('lastDividendValue') or current_info.get('dividendRate') or current_info.get('forwardDividendRate')
        last_split = current_info.get('lastSplitFactor') or current_info.get('lastSplitDate')
        result_df.loc['dividend_and_split'] = pd.Series({**{y: None for y in YEARS_TO_EXTRACT}, **{y: divsplit.get(y) for y in YEARS_TO_EXTRACT}, 'actual': {'lastDividend': last_div, 'lastSplit': last_split}})

        # --- Payout ratio: (annual dividends per share) / EPS por año ---
        payout = {}
        for year in YEARS_TO_EXTRACT:
            eps = eps_data.get(year) if year in eps_data else None
            annual_div = None
            if isinstance(price_hist, pd.DataFrame):
                mask = price_hist.index.year == year
                if mask.any():
                    annual_div = price_hist.loc[mask, 'Dividends'].sum()
            if eps is None or eps == 0 or annual_div is None:
                payout[year] = None
            else:
                payout[year] = (annual_div / eps) if eps else None
        payout['actual'] = current_info.get('payoutRatio')
        result_df.loc['payoutRatio'] = pd.Series(payout)

        # --- Market cap por año: sharesOutstanding * price de fin de año ---
        marketcap = {}
        for year in YEARS_TO_EXTRACT:
            close_price = get_year_end_price_series(price_hist, year) if isinstance(price_hist, pd.DataFrame) else None
            if shares_outstanding and close_price:
                marketcap[year] = shares_outstanding * close_price
            else:
                marketcap[year] = None
        marketcap['actual'] = current_info.get('marketCap')
        result_df.loc['marketCap'] = pd.Series(marketcap)

        # --- Beta: estimate per-year using covariance with S&P500 daily returns ---
        beta_data = {}
        for year in YEARS_TO_EXTRACT:
            try:
                if isinstance(price_hist, pd.DataFrame) and market_hist is not None:
                    mask_s = price_hist.index.year == year
                    mask_m = market_hist.index.year == year
                    if mask_s.any() and mask_m.any() and 'Close' in price_hist.columns and 'Close' in market_hist.columns:
                        returns_s = price_hist.loc[mask_s, 'Close'].pct_change().dropna()
                        returns_m = market_hist.loc[mask_m, 'Close'].pct_change().dropna()
                        combined = pd.concat([returns_s, returns_m], axis=1, keys=['stock', 'market']).dropna()
                        if not combined.empty and combined['market'].var() != 0:
                            cov = combined.cov().iloc[0,1]
                            beta_val = cov / combined['market'].var()
                            beta_data[year] = float(beta_val)
                        else:
                            beta_data[year] = None
                    else:
                        beta_data[year] = None
                else:
                    beta_data[year] = None
            except Exception:
                beta_data[year] = None
        beta_data['actual'] = current_info.get('beta')
        result_df.loc['beta'] = pd.Series(beta_data)
        result_df.loc['peRatio'] = pd.Series({'actual': current_info.get('trailingPE'), **{y: None for y in YEARS_TO_EXTRACT}})
        result_df.loc['trailingPE'] = pd.Series({'actual': current_info.get('trailingPE'), **{y: None for y in YEARS_TO_EXTRACT}})
        result_df.loc['forwardPE'] = pd.Series({'actual': current_info.get('forwardPE'), **{y: None for y in YEARS_TO_EXTRACT}})
        result_df.loc['forwardDividendRate'] = pd.Series({'actual': current_info.get('forwardDividendRate') or current_info.get('dividendRate'), **{y: None for y in YEARS_TO_EXTRACT}})
        f52_low = current_info.get('fiftyTwoWeekLow')
        f52_high = current_info.get('fiftyTwoWeekHigh')
        # Compute per-year high/low using price_hist (similar to the example provided)
        range_data = {}
        if isinstance(price_hist, pd.DataFrame) and 'High' in price_hist.columns and 'Low' in price_hist.columns:
            for year in YEARS_TO_EXTRACT:
                mask = price_hist.index.year == year
                if mask.any():
                    max_price = price_hist.loc[mask, 'High'].max()
                    min_price = price_hist.loc[mask, 'Low'].min()
                    if pd.notna(max_price) and pd.notna(min_price):
                        range_data[year] = f"{min_price}-{max_price}"
                    else:
                        range_data[year] = None
                else:
                    range_data[year] = None
        else:
            for year in YEARS_TO_EXTRACT:
                range_data[year] = None
        range_data['actual'] = f"{f52_low}-{f52_high}" if f52_low and f52_high else None
        result_df.loc['52WeekRange'] = pd.Series(range_data)

        # --- Balance sheet derived fields requested by user ---
        # We'll extract common names from the balance_sheet DataFrame when available.
        # Use display labels matching the user's requested CSV rows.
        # Candidate field names may vary across tickers; try several common variants.
        def safe_bs_get(date, candidates):
            return get_value_candidates_normalized(balance_sheet, candidates, date)

        cash_eq = {}
        total_assets = {}
        total_liabilities = {}
        total_current_assets = {}
        total_current_liabilities = {}
        intangible_assets = {}
        goodwill = {}
        long_term_debt = {}
        short_term_debt = {}
        total_debts = {}
        ordinary_shares = {}
        net_tangible_assets = {}
        working_cap = {}
        invested_cap = {}

        for date in (balance_sheet.columns if isinstance(balance_sheet, pd.DataFrame) else []):
            year = _col_year(date)
            if year is None or year not in YEARS_TO_EXTRACT:
                continue
            # candidates
            cash = safe_bs_get(date, ['Cash And Cash Equivalents', 'Cash And Cash Equivalents (Total)', 'Cash', 'cash'])
            ta = safe_bs_get(date, ['Total Assets', 'totalAssets', 'TotalAssets'])
            tl = safe_bs_get(date, ['Total Liab', 'Total Liabilities', 'totalLiab', 'totalLiabilities'])
            tca = safe_bs_get(date, ['Total Current Assets', 'TotalCurrentAssets', 'totalCurrentAssets'])
            tcl = safe_bs_get(date, ['Total Current Liabilities', 'TotalCurrentLiabilities', 'totalCurrentLiabilities'])
            ia = safe_bs_get(date, ['Intangible Assets', 'intangibleAssets', 'Goodwill And Intangible Assets'])
            gw = safe_bs_get(date, ['Goodwill', 'goodWill'])
            ltd = safe_bs_get(date, ['Long Term Debt', 'Long-term Debt', 'longTermDebt'])
            std = safe_bs_get(date, ['Short Long Term Debt', 'Short Term Debt', 'Short-term Debt', 'shortTermDebt'])
            # ordinary shares may be in income_statement/financials as 'Basic Average Shares' etc.
            ord_sh = None
            try:
                ord_sh = get_value_candidates_normalized(income_statement, ['Basic Average Shares', 'Basic Average Shares (Shares)', 'BasicAverageShares', 'Basic EPS Shares', 'Basic Shares', 'Weighted Average Shares', 'WeightedAverageShares'], date)
            except Exception:
                ord_sh = None

            cash_eq[year] = cash
            total_assets[year] = ta
            total_liabilities[year] = tl
            total_current_assets[year] = tca
            total_current_liabilities[year] = tcl
            intangible_assets[year] = ia
            goodwill[year] = gw
            long_term_debt[year] = ltd
            short_term_debt[year] = std
            ordinary_shares[year] = ord_sh

            # total debts: sum available debt pieces
            td = None
            try:
                parts = [x for x in (ltd, std) if x is not None]
                td = sum(parts) if parts else None
            except Exception:
                td = None
            total_debts[year] = td

            # working capital: total current assets - total current liabilities
            if tca is not None and tcl is not None:
                working_cap[year] = tca - tcl
            else:
                working_cap[year] = None

            # invested capital: simple proxy = total assets - total current liabilities - cash
            if ta is not None:
                try:
                    used_liab = tcl if tcl is not None else (tl if tl is not None else 0)
                    invested_cap[year] = ta - (used_liab if used_liab is not None else 0) - (cash if cash is not None else 0)
                except Exception:
                    invested_cap[year] = None
            else:
                invested_cap[year] = None

            # net tangible assets = total assets - intangible assets - goodwill
            if ta is not None:
                nta = ta - (ia if ia is not None else 0) - (gw if gw is not None else 0)
                net_tangible_assets[year] = nta
            else:
                net_tangible_assets[year] = None

        # actual/current values (from info when available)
        ordinary_shares['actual'] = current_info.get('sharesOutstanding')
        cash_eq['actual'] = None
        total_assets['actual'] = None
        total_liabilities['actual'] = None
        working_cap['actual'] = None
        invested_cap['actual'] = None
        total_debts['actual'] = None
        net_tangible_assets['actual'] = None

        # Insert rows with display names matching the user's requested CSV labels
        result_df.loc['cash cash equivalence'] = pd.Series(cash_eq)
        result_df.loc['total assets'] = pd.Series(total_assets)
        result_df.loc['total liabilities'] = pd.Series(total_liabilities)
        result_df.loc['working capital'] = pd.Series(working_cap)
        result_df.loc['invested capital'] = pd.Series(invested_cap)
        result_df.loc['total debts'] = pd.Series(total_debts)
        result_df.loc['ordinary shared number'] = pd.Series(ordinary_shares)
        result_df.loc['net tangible assets'] = pd.Series(net_tangible_assets)

        # Asegurar columnas en orden YEARS_TO_EXTRACT + ['actual']
        cols_order = YEARS_TO_EXTRACT + ['actual']
        result_df = result_df.reindex(index=CSV_ROW_NAMES)
        for col in cols_order:
            if col not in result_df.columns:
                result_df[col] = None
        result_df = result_df[cols_order]

        # Insert metadata columnas al inicio: ticker, as_of (current date | current price), code/year
        result_df.insert(0, ticker_symbol, pd.NA)
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        as_of_value = f"{current_date_str} | {current_price}"
        result_df.insert(1, 'as_of', pd.Series([as_of_value] * len(result_df), index=result_df.index))
        result_df.insert(2, 'code/year', result_df.index)

        return result_df

    except Exception as e:
        # Use logging.exception to include traceback for debugging purposes
        logging.exception(f"Ocurrió un error inesperado al obtener o calcular datos para {ticker_symbol}: {e}")
        return None