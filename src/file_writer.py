# src/file_writer.py

import pandas as pd
import os
import logging
from datetime import datetime
from config import OUTPUT_DIRECTORY, YEARS_TO_EXTRACT

def save_to_csv(df: pd.DataFrame, ticker: str):
    """
    Guarda el DataFrame en un archivo CSV en el directorio de salida.
    """
    try:
        # Asegurarse que el directorio de salida exista
        if not os.path.exists(OUTPUT_DIRECTORY):
            os.makedirs(OUTPUT_DIRECTORY)

        # Generar nombre de archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_annual_data_{timestamp}.csv"
        filepath = os.path.join(OUTPUT_DIRECTORY, filename)

        # We'll produce two CSVs: a raw machine-friendly CSV and a human-readable CSV.
        years = list(YEARS_TO_EXTRACT)
        cols_order = years + ['actual']

        import csv

        def _format_number_for_human(val, scale='M'):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ''
            try:
                v = float(val)
            except Exception:
                return str(val)
            if scale == 'M':
                v_scaled = v / 1_000_000.0
                return f"{v_scaled:,.2f} M"
            if scale == 'B':
                v_scaled = v / 1_000_000_000.0
                return f"{v_scaled:,.2f} B"
            return f"{v:,.2f}"

        def _format_52week_range(val):
            """Format a range like 'min-max' to one decimal place per endpoint."""
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ''
            try:
                s = str(val)
                if '-' in s:
                    parts = s.split('-')
                    if len(parts) >= 2:
                        a = float(parts[0])
                        b = float(parts[1])
                        return f"{a:.1f}-{b:.1f}"
                # fallback: try to parse single number
                num = float(s)
                return f"{num:.1f}"
            except Exception:
                return s

        def _format_percent(val):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return ''
            try:
                return f"{float(val) * 100:.2f}%"
            except Exception:
                return str(val)

        def _write_grouped_csv(path, human_readable: bool):
            with open(path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                # First row: ticker (A1), date (B1) and current price (C1)
                as_of_raw = ''
                if 'as_of' in df.columns:
                    try:
                        as_of_raw = df.iloc[0]['as_of']
                    except Exception:
                        as_of_raw = ''
                date_cell = ''
                price_cell = ''
                if isinstance(as_of_raw, str) and '|' in as_of_raw:
                    parts = [p.strip() for p in as_of_raw.split('|', 1)]
                    if len(parts) >= 1:
                        date_cell = parts[0]
                    if len(parts) == 2:
                        price_cell = parts[1]
                else:
                    # fallback: try to read 'actual' price from df or leave empty
                    price_cell = ''

                writer.writerow([ticker, date_cell, price_cell])
                writer.writerow([])

                # Valores representativos
                writer.writerow(['Valores representativos'] + cols_order)

                # Define rep metrics but expand dividends into two rows: 'dividends' and 'splits'
                rep_metrics = [
                    'marketCap', 'beta', 'peRatio', 'forwardDividendYield', 'EPS', '52WeekRange',
                    'trailingPE', 'forwardPE', 'profitMargin', 'payoutRatio', 'ROE'
                ]

                for m in rep_metrics:
                    row = [m]
                    for c in cols_order:
                        val = df.at[m, c] if m in df.index else None
                        if human_readable:
                            if m in ('marketCap',):
                                out = _format_number_for_human(val, scale='M')
                            elif m in ('totalRevenue', 'costOfRevenue'):
                                out = _format_number_for_human(val, scale='M')
                            elif m in ('operatingExpense', 'netIncome'):
                                out = _format_number_for_human(val, scale='M')
                            elif m in ('profitMargin', 'ROE', 'payoutRatio', 'forwardDividendYield'):
                                out = _format_percent(val)
                            elif m in ('EPS', 'trailingPE', 'forwardPE', 'beta', 'peRatio'):
                                out = _format_number_for_human(val, scale=None)
                            elif m == '52WeekRange':
                                out = _format_52week_range(val)
                            else:
                                out = '' if pd.isna(val) else str(val)
                        else:
                            # raw
                            out = '' if pd.isna(val) else val
                        row.append(out)
                    writer.writerow(row)

                # dividends and splits expanded
                # dividends row
                drow = ['dividends']
                srow = ['splits']
                for c in cols_order:
                    raw = df.at['dividend_and_split', c] if 'dividend_and_split' in df.index else None
                    if isinstance(raw, dict):
                        div = raw.get('dividends')
                        splits = raw.get('splits')
                    else:
                        div = None
                        splits = None
                    if human_readable:
                        drow.append('' if pd.isna(div) or div is None else _format_number_for_human(div, scale=None))
                        # splits: list -> join
                        if isinstance(splits, list):
                            srow.append(';'.join(splits) if splits else '')
                        else:
                            srow.append('' if splits is None else str(splits))
                    else:
                        drow.append('' if pd.isna(div) or div is None else div)
                        if isinstance(splits, list):
                            srow.append(';'.join(splits) if splits else '')
                        else:
                            srow.append('' if splits is None else str(splits))
                writer.writerow(drow)
                writer.writerow(srow)

                # Financials
                writer.writerow([])
                writer.writerow(['financials'] + cols_order)
                fin_metrics = ['totalRevenue', 'totalRevenueChange', 'costOfRevenue', 'operatingExpense', 'netIncome', 'EBITDA', 'net debts over EBITDA']
                for m in fin_metrics:
                    row = [m]
                    for c in cols_order:
                        val = df.at[m, c] if m in df.index else None
                        if human_readable and m in ('totalRevenue', 'costOfRevenue', 'operatingExpense', 'netIncome', 'EBITDA'):
                            out = _format_number_for_human(val, scale='M')
                        elif human_readable and m in ('totalRevenueChange', 'net debts over EBITDA',):
                            out = _format_percent(val)
                        else:
                            out = '' if pd.isna(val) else val
                        row.append(out)
                    writer.writerow(row)

                # Balance sheets
                writer.writerow([])
                writer.writerow(['balance sheets'] + cols_order)
                bs_metrics = [
                    'cash cash equivalence', 'total assets', 'total liabilities', 'working capital',
                    'invested capital', 'net debts', 'ordinary shared number', 'net tangible assets'
                ]
                for m in bs_metrics:
                    row = [m]
                    for c in cols_order:
                        val = df.at[m, c] if m in df.index else None
                        if human_readable and m in ('cash cash equivalence', 'total assets', 'invested capital', 'net debts', 'net tangible assets', 'total liabilities', 'working capital'):
                            out = _format_number_for_human(val, scale='M')
                        else:
                            out = '' if pd.isna(val) else val
                        row.append(out)
                    writer.writerow(row)

        # write raw file
        raw_path = filepath.replace('.csv', '_raw.csv')
        _write_grouped_csv(raw_path, human_readable=False)
        logging.info(f"Archivo raw guardado exitosamente en: {raw_path}")

        # write readable file
        readable_path = filepath.replace('.csv', '_readable.csv')
        _write_grouped_csv(readable_path, human_readable=True)
        logging.info(f"Archivo readable guardado exitosamente en: {readable_path}")
        return raw_path, readable_path

    except Exception as e:
        logging.error(f"Error al guardar el archivo CSV: {e}")
        return None
