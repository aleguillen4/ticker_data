# Proyecto de Extracción de Datos de Yahoo Finance

Este proyecto contiene un script de Python para extraer métricas financieras fundamentales (PE, EPS TTM, ROE) de Yahoo Finance para un ticker específico y guardarlas en un archivo `.csv`.

## 1. Setup (Instalación)

Se requiere Python 3.8 o superior.

1.  **Clonar el Repositorio**
    ```bash
    git clone <url-del-repositorio>
    cd proyecto-yahoo-finance
    ```

2.  **Crear un Entorno Virtual**
    ```bash
    python -m venv venv
    ```

3.  **Activar el Entorno Virtual**
    * En macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    * En Windows (PowerShell):
        ```bash
        .\venv\Scripts\Activate.ps1
        ```
    * En Windows (CMD):
        ```bash
        .\venv\Scripts\activate.bat
        ```

4.  **Instalar Dependencias**
    ```bash
    pip install -r requirements.txt
    ```

## 2. Configuración (Opcional)

Puedes modificar las métricas a extraer o el directorio de salida editando el archivo `config.py`.

* `OUTPUT_DIRECTORY`: Carpeta donde se guardarán los CSV.
* `METRICS_OF_INTEREST`: Diccionario que mapea las claves de `yfinance.info` a los nombres de columna deseados.

## 3. Uso

Ejecuta el script desde la raíz del proyecto, pasando el ticker deseado como argumento.

**Sintaxis:**
```bash
python src/main.py <TICKER>