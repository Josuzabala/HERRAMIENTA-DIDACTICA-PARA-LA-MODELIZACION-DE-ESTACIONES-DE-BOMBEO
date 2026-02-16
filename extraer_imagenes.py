"""
Script para extraer imágenes del PDF del TFG y clasificarlas en:
- figuras/ : Imágenes con título "Figura X.X: ..."
- tablas/ : Imágenes de tablas (con título "Tabla X.X: ...")
- otros/ : Logos, enunciados, ecuaciones, procedimientos (sin título)

Basado en el análisis del PDF TFG.pdf (53 páginas)
"""

import fitz  # PyMuPDF
import os
from pathlib import Path

# Rutas
PDF_PATH = "TFG.pdf"
BASE_DIR = Path(".")

# Crear carpetas si no existen
for folder in ["figuras", "tablas", "otros"]:
    (BASE_DIR / folder).mkdir(exist_ok=True)

# Clasificación basada en el análisis exacto del PDF
# Página (1-indexed) -> lista de (nombre, carpeta)
# Según el texto del PDF:
# - Página 8: Tabla 2.1 (expresiones f)
# - Página 9: Figura 2.1 (Moody)
# - Página 10: Tabla 2.2 (J1)
# - Página 11: Tabla 2.3 (Chw)
# - Página 12: Tabla 2.4 (longitud equivalente)
# - Página 14: Figura 2.2 (esquema instalación)
# - Página 15: Figura 2.3 (CCI)
# - Página 16: Figura 2.4 (CCB) + Figura 2.5 (punto func)
# - Página 18: Figura 2.6 (esquema aspiración)
# - Página 20: Figura 2.7 (pitting) - NO, es logo NumPy
# - Página 24: Figura 3.1 (esquema prob3)
# etc.

# CORRECCIÓN: Las páginas en PyMuPDF son 0-indexed
CLASIFICACION = {
    # Página 1 (índice 0) - Logo UPV/EHU
    0: [("logo_upv_ehu", "otros")],
    
    # Página 9 (índice 8) - Según PDF content: "Tabla 2.1. Expresiones empíricas..."
    # PERO la imagen en pág 9 del PDF real es el Diagrama de Moody (Figura 2.1)
    # El texto de Tabla 2.1 está en página 8, la imagen Moody en página 9
    8: [("figura_2_1_moody", "figuras")],
    
    # Página 10 (índice 9) - Tabla 2.2 (valores J1)
    9: [("tabla_2_2_j1", "tablas")],
    
    # Página 11 (índice 10) - Tabla 2.3 (Chw)
    10: [("tabla_2_3_chw", "tablas")],
    
    # Página 12 (índice 11) - Tabla 2.4 (longitud equivalente)
    11: [("tabla_2_4_longitud_equiv", "tablas")],
    
    # Página 14 (índice 13) - Figura 2.2 (esquema instalación) + Figura 2.3 (CCI)
    # NOTA: Solo hay 1 imagen, es el esquema
    13: [("figura_2_2_esquema_instalacion", "figuras")],
    
    # Página 15 (índice 14) - Figura 2.3 (CCI)
    14: [("figura_2_3_cci", "figuras")],
    
    # Página 16 (índice 15) - Figura 2.4 (CCB bomba) + Figura 2.5 (punto func)
    # 2 imágenes en esta página
    15: [("figura_2_4_ccb_bomba", "figuras"), ("figura_2_5_punto_func", "figuras")],
    
    # Página 18 (índice 17) - Figura 2.6 (esquema aspiración)
    17: [("figura_2_6_esquema_aspiracion", "figuras")],
    
    # Página 20 (índice 19) - Logo NumPy (sin título, en sección librerías)
    19: [("logo_numpy", "otros")],
    
    # Página 24 (índice 23) - Figura 3.1 (esquema hidráulico prob3)
    23: [("figura_3_1_esquema_prob3", "figuras")],
    
    # Página 25 (índice 24) - Figura 3.2 (diseño terminal)
    24: [("figura_3_2_terminal", "figuras")],
    
    # Página 26 (índice 25) - Figura 3.3 (diseño CustomTkinter final)
    25: [("figura_3_3_customtkinter", "figuras")],
    
    # Página 27 (índice 26) - Enunciado problema 1 (imagen sin título)
    26: [("enunciado_prob1", "otros")],
    
    # Página 28 (índice 27) - Ecuación problema 1
    27: [("ecuacion_prob1", "otros")],
    
    # Página 29 (índice 28) - Ecuaciones + Tabla 4.1 (válvula)
    28: [("ecuacion_hmi", "otros"), ("tabla_4_1_valvula", "tablas")],
    
    # Página 30 (índice 29) - Figura 4.1 (CCI válvula 70%)
    29: [("figura_4_1_cci_valvula70", "figuras")],
    
    # Página 31 (índice 30) - Figura 4.2 (CCI válvula 30%)
    30: [("figura_4_2_cci_valvula30", "figuras")],
    
    # Página 32 (índice 31) - Figura 4.3 (CCI Q=0)
    31: [("figura_4_3_q0", "figuras")],
    
    # Página 33 (índice 32) - Figura 4.4 (interfaz prob1) + Tabla 4.2
    32: [("figura_4_4_interfaz_prob1", "figuras"), ("tabla_4_2_comparacion", "tablas")],
    
    # Página 34 (índice 33) - Continuación tabla o enunciado prob2
    33: [("enunciado_prob2_parte1", "otros")],
    
    # Página 35 (índice 34) - Enunciado prob2 parte 2
    34: [("enunciado_prob2_parte2", "otros")],
    
    # Página 36 (índice 35) - Ecuaciones prob2
    35: [("ecuacion_prob2_1", "otros"), ("ecuacion_prob2_2", "otros"), ("ecuacion_prob2_3", "otros")],
    
    # Página 37 (índice 36) - Figura 4.5 (bomba INP) + tabla Q-Hmi
    36: [("figura_4_5_bomba_inp", "figuras"), ("tabla_q_hmi", "tablas")],
    
    # Página 38 (índice 37) - Figura 4.6 (interfaz prob2) + Tabla 4.3
    37: [("figura_4_6_interfaz_prob2", "figuras"), ("tabla_4_3_resultados", "tablas")],
    
    # Página 39 (índice 38) - Enunciado prob4 + gráfico NPSH
    38: [("enunciado_prob4", "otros")],
    
    # Página 40 (índice 39) - Interfaz prob4 grande
    39: [("figura_interfaz_prob4", "figuras")],
    
    # Página 41 (índice 40) - Captura parámetros
    40: [("captura_parametros", "otros")],
    
    # Página 43 (índice 42) - Gráficos NPSH
    42: [("figura_graficos_npsh", "figuras")],
    
    # Página 46 (índice 45) - Figura cavitación/verificación
    45: [("figura_verificacion_cavitacion", "figuras")],
    
    # Página 47 (índice 46) - Ecuación final
    46: [("ecuacion_final", "otros")],
}

def extraer_imagenes():
    """Extrae todas las imágenes del PDF y las guarda con nombres descriptivos."""
    
    doc = fitz.open(PDF_PATH)
    print(f"PDF abierto: {PDF_PATH}")
    print(f"Total de páginas: {doc.page_count}")
    
    imagenes_extraidas = {"figuras": 0, "tablas": 0, "otros": 0}
    imagenes_no_clasificadas = []
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        image_list = page.get_images()
        
        if not image_list:
            continue
            
        print(f"\nPágina {page_num + 1}: {len(image_list)} imagen(es)")
        
        # Si tenemos clasificación para esta página
        if page_num in CLASIFICACION:
            clasificaciones = CLASIFICACION[page_num]
            
            for idx, img_info in enumerate(image_list):
                xref = img_info[0]
                width, height = img_info[2], img_info[3]
                
                if idx < len(clasificaciones):
                    nombre, carpeta = clasificaciones[idx]
                else:
                    # Imagen extra no prevista
                    nombre = f"extra_pag{page_num + 1}_{idx + 1}"
                    carpeta = "otros"
                    imagenes_no_clasificadas.append((page_num + 1, idx, width, height))
                
                # Extraer imagen
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Guardar
                    filename = f"{nombre}.{image_ext}"
                    filepath = BASE_DIR / carpeta / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                    
                    print(f"  ✓ {carpeta}/{filename} ({width}x{height})")
                    imagenes_extraidas[carpeta] += 1
                    
                except Exception as e:
                    print(f"  ✗ ERROR extrayendo imagen {idx}: {e}")
        else:
            # Página sin clasificación previa
            for idx, img_info in enumerate(image_list):
                xref = img_info[0]
                width, height = img_info[2], img_info[3]
                
                imagenes_no_clasificadas.append((page_num + 1, idx, width, height))
                
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    nombre = f"sin_clasificar_pag{page_num + 1}_{idx + 1}"
                    filename = f"{nombre}.{image_ext}"
                    filepath = BASE_DIR / "otros" / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                    
                    print(f"  ? otros/{filename} ({width}x{height}) [SIN CLASIFICAR]")
                    imagenes_extraidas["otros"] += 1
                    
                except Exception as e:
                    print(f"  ✗ ERROR: {e}")
    
    doc.close()
    
    print("\n" + "="*60)
    print("RESUMEN DE EXTRACCIÓN:")
    print(f"  📊 Figuras: {imagenes_extraidas['figuras']}")
    print(f"  📋 Tablas: {imagenes_extraidas['tablas']}")
    print(f"  📝 Otros: {imagenes_extraidas['otros']}")
    print(f"  ─────────────────────")
    print(f"  TOTAL: {sum(imagenes_extraidas.values())} imágenes")
    
    if imagenes_no_clasificadas:
        print(f"\n⚠️  {len(imagenes_no_clasificadas)} imagen(es) sin clasificación previa:")
        for pag, idx, w, h in imagenes_no_clasificadas:
            print(f"     - Página {pag}, imagen {idx} ({w}x{h})")


def listar_imagenes_por_pagina():
    """Lista todas las imágenes del PDF para ayudar con la clasificación."""
    
    doc = fitz.open(PDF_PATH)
    print(f"PDF: {PDF_PATH}")
    print(f"Páginas: {doc.page_count}\n")
    
    total = 0
    for page_num in range(doc.page_count):
        page = doc[page_num]
        image_list = page.get_images()
        
        if image_list:
            print(f"Página {page_num + 1} ({len(image_list)} imagen(es)):")
            for idx, img in enumerate(image_list):
                xref, smask, width, height = img[0], img[1], img[2], img[3]
                print(f"  [{idx}] xref={xref}, {width}x{height}")
                total += 1
    
    print(f"\nTotal: {total} imágenes")
    doc.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--listar":
        listar_imagenes_por_pagina()
    else:
        extraer_imagenes()
