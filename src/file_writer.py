# src/file_writer.py

import pandas as pd
import os
import logging
from datetime import datetime
from config import OUTPUT_DIRECTORY

def save_to_csv(df: pd.DataFrame, ticker: str):
    """
    Guarda el DataFrame en un archivo CSV en el directorio de salida.
    El nombre del archivo incluirá el ticker y un timestamp.
    """
    try:
        # Asegurarse que el directorio de salida exista
        if not os.path.exists(OUTPUT_DIRECTORY):
            os.makedirs(OUTPUT_DIRECTORY)
            logging.info(f"Directorio creado: {OUTPUT_DIRECTORY}")

        # Generar nombre de archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_fundamentals_{timestamp}.csv"
        filepath = os.path.join(OUTPUT_DIRECTORY, filename)

        # Guardar el archivo
        # index=False para no incluir el índice numérico de pandas en el CSV
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logging.info(f"Archivo guardado exitosamente en: {filepath}")
        return filepath

    except Exception as e:
        logging.error(f"Error al guardar el archivo CSV: {e}")
        return None