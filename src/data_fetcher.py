# src/data_fetcher.py

import yfinance as yf
import pandas as pd
import logging
from config import METRICS_OF_INTEREST, CSV_COLUMN_NAMES

def get_stock_fundamentals(ticker_symbol: str) -> pd.DataFrame:
    """
    Obtiene los datos fundamentales (PE, ROE, etc.) para un ticker específico
    usando la propiedad .info de yfinance.
    """
    try:
        logging.info(f"Conectando a Yahoo Finance para obtener datos de {ticker_symbol}...")
        ticker = yf.Ticker(ticker_symbol)
        
        # .info devuelve un diccionario grande con todos los datos
        info = ticker.info

        # Verificamos si yfinance devolvió datos (un diccionario vacío significa error)
        if not info or 'symbol' not in info:
            logging.error(f"No se encontraron datos para el ticker: {ticker_symbol}. Puede ser un ticker inválido.")
            return None

        logging.info(f"Datos recibidos. Extrayendo métricas de interés...")
        
        # Extraemos solo las métricas que definimos en config.py
        data = {}
        for key, display_name in METRICS_OF_INTEREST.items():
            # Usamos .get() para evitar errores si una métrica falta (devuelve None)
            data[display_name] = info.get(key)

        # Convertimos nuestro diccionario de datos a un DataFrame de Pandas
        # Usamos CSV_COLUMN_NAMES para asegurar el orden correcto de las columnas
        df = pd.DataFrame([data], columns=CSV_COLUMN_NAMES)
        
        return df

    except Exception as e:
        logging.error(f"Ocurrió un error inesperado al obtener datos para {ticker_symbol}: {e}")
        return None