# src/main.py

import argparse
import logging
#from src.data_fetcher import get_stock_fundamentals
from src.data_fetcher import get_annual_fundamentals
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
    data_df, red_cells, green_cells = get_annual_fundamentals(ticker)
    
    # 2. Guardar datos
    if data_df is not None and not data_df.empty:
        logging.info("Datos fundamentales extraídos:")
        # Imprime el DataFrame como un string limpio
        logging.info("\n" + data_df.to_string(index=False))
        
        save_to_csv(data_df, ticker, red_cells=red_cells, green_cells=green_cells)
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
    
    # Argumento posicional opcional (si no se pasa, se puede usar --tickers-file)
    parser.add_argument(
        "ticker",
        type=str,
        nargs='?',
        help="El símbolo del ticker a consultar (ej: AAPL, MSFT, GOOGL). Si se omite, use --tickers-file."
    )

    parser.add_argument(
        "--tickers-file",
        dest="tickers_file",
        type=str,
        help="Ruta a un archivo de texto con una lista de tickers (uno por línea). Ejemplo: tickers.txt"
    )
    
    args = parser.parse_args()
    
    # Ejecutar el pipeline
    if args.tickers_file:
        try:
            with open(args.tickers_file, 'r', encoding='utf-8') as f:
                lines = [ln.strip() for ln in f.readlines()]
            tickers = [ln for ln in lines if ln and not ln.startswith('#')]
            if not tickers:
                logging.error(f"El archivo {args.tickers_file} no contiene tickers válidos.")
                return
            for t in tickers:
                run_pipeline(t)
        except FileNotFoundError:
            logging.error(f"Archivo de tickers no encontrado: {args.tickers_file}")
        except Exception as e:
            logging.exception(f"Error leyendo el archivo de tickers: {e}")
    elif args.ticker:
        run_pipeline(args.ticker)
    else:
        logging.error("Debe pasar un ticker como argumento o usar --tickers-file <archivo> con la lista de tickers.")

if __name__ == "__main__":
    # Esto permite que el script sea ejecutado directamente
    # (ej: python src/main.py AAPL)
    main()
