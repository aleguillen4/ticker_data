# src/main.py

import argparse
import logging
from src.data_fetcher import get_stock_fundamentals
from src.file_writer import save_to_csv
from src.utils import setup_logging

def run_pipeline(ticker: str):
    """
    Orquesta el flujo principal de la aplicación.
    1. Obtiene datos
    2. Guarda datos
    """
    logging.info(f"Iniciando proceso para el ticker: {ticker.upper()}...")
    
    # 1. Obtener datos
    data_df = get_stock_fundamentals(ticker)
    
    # 2. Guardar datos
    if data_df is not None and not data_df.empty:
        logging.info("Datos fundamentales extraídos:")
        # Imprime el DataFrame como un string limpio
        logging.info("\n" + data_df.to_string(index=False))
        
        save_to_csv(data_df, ticker)
        logging.info(f"Proceso completado para {ticker.upper()}.")
    else:
        logging.warning(f"No se generó ningún archivo CSV para {ticker.upper()} debido a errores previos.")

def main():
    """Punto de entrada principal con parsing de argumentos."""
    
    # Configurar el logger primero
    setup_logging()

    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(
        description="Cliente de Yahoo Finance para extraer datos fundamentales."
    )
    
    # Argumento posicional, es obligatorio
    parser.add_argument(
        "ticker", 
        type=str, 
        help="El símbolo del ticker a consultar (ej: AAPL, MSFT, GOOGL)."
    )
    
    args = parser.parse_args()
    
    # Ejecutar el pipeline
    run_pipeline(args.ticker)

if __name__ == "__main__":
    # Esto permite que el script sea ejecutado directamente
    # (ej: python src/main.py AAPL)
    main()