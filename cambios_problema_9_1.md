# Documentación de Cambios - Problema nº1 (Válvula de Impulsión)

## 1. Descripción General
Se ha actualizado el modelo de la válvula de regulación situada en la tubería de impulsión para reflejar fielmente el comportamiento de una válvula comercial real, basándose en las curvas características proporcionadas por el fabricante ($K_v$ vs Grado de Apertura).

Las principales modificaciones son:
- Sustitución de la apertura porcentual (0-100%) por **grados de apertura sexagesimales (0° - 90°)**.
- Restricción del diámetro de la válvula a valores comerciales estandarizados.
- Implementación de una nueva fórmula de pérdidas de carga basada en el coeficiente de caudal $K_v$.
- Incorporación de una tabla de datos $K_v$ extraída mediante lectura estricta del gráfico del fabricante.

## 2. Diámetros y Rango de Operación

### Diámetros de Válvula ($D_2$)
El usuario ahora solo puede seleccionar diámetros comerciales para la válvula. El diámetro seleccionado determina la curva $K_v$ que se utilizará en los cálculos.
*   **Diámetros disponibles:** 100 mm, 150 mm, 200 mm, 250 mm, 300 mm.

### Grado de Apertura
La regulación se realiza mediante un ángulo de giro, típico de válvulas de mariposa o bola.
*   **Rango:** 0° (Cerrada) a 90° (Totalmente abierta).
*   **Paso:** 10°.

## 3. Fórmula de Pérdidas de Carga
La pérdida de carga introducida por la válvula ($h_f$) se calcula ahora utilizando el coeficiente de caudal $K_v$, que relaciona el caudal con la caída de presión.

La fórmula implementada es:

$$ h_f = \frac{Q^2}{K_v^2} \cdot \frac{10}{s} $$

Donde:
*   $h_f$: Pérdida de carga en metros de columna de líquido (m.c.l.).
*   $Q$: Caudal circulante en $m^3/h$.
*   $K_v$: Coeficiente de caudal en $m^3/h / \sqrt{kg/cm^2}$ (obtenido de la tabla).
*   $s$: Densidad relativa del fluido (adimensional, típicamente 1.0 para agua, 1.2 en este problema).
*   $10$: Factor de conversión de unidades de presión ($kg/cm^2$ a m.c.l. aprox).

## 4. Tabla de Coeficientes $K_v$
Los valores de $K_v$ se han determinado interpolando visualmente de forma estricta las curvas del gráfico del fabricante para cada diámetro y cada salto de 10°.

> **Nota:** Cuando la curva del fabricante superaba el límite del gráfico ($K_v > 500$), se ha acotado el valor a 500 para mantener la consistencia en la visualización, asumiendo que la pérdida se mantiene mínima y constante a partir de ese punto.

| Grados ($^\circ$) | $D=100mm$ | $D=150mm$ | $D=200mm$ | $D=250mm$ | $D=300mm$ |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0°** | 0 | 0 | 0 | 0 | 0 |
| **10°** | 2 | 3 | 5 | 8 | 12 |
| **20°** | 7 | 12 | 20 | 32 | 48 |
| **30°** | 18 | 32 | 50 | 75 | 115 |
| **40°** | 38 | 62 | 95 | 140 | 205 |
| **50°** | 65 | 105 | 155 | 230 | 340 |
| **60°** | 102 | 160 | 230 | 340 | 500* |
| **70°** | 150 | 235 | 320 | 470 | 500* |
| **80°** | 210 | 320 | 420 | 500* | 500* |
| **90°** | 280 | 420 | 500* | 500* | 500* |

*\* Valor acotado al límite superior del gráfico disponible.*

## 5. Lógica de Interpolación
Para aperturas intermedias (ej. 45°) o diámetros no exactos (si se permitiera en el futuro), el software realiza una:
1.  **Selección de Diámetro:** Escoge la tabla correspondiente al diámetro comercial más cercano.
2.  **Interpolación Lineal:** Calcula el valor exacto de $K_v$ interpolando linealmente entre los dos valores de apertura más cercanos (ej. entre 40° y 50°).

---
**Fecha de actualización:** 18/01/2026
