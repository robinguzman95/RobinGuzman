# Valor esperado y potencia (Fase 5)

Datos: tablas de premios publicadas por baloto.com para cada sorteo del último año
(3 nov 2025 – 3 nov 2026): 156 sorteos de Baloto y Revancha, 203 de MiLoto y 102 de ColorLoto.
Faltan los 10 sorteos de julio de 2026 que baloto.com no publica. Regenerar con
`uv run lotolab scrape-prizes` y `uv run lotolab expected-value`.

## ¿Vale la pena jugar?

| Juego | Precio | Vuelve en promedio (acumulado actual) | Sin premio mayor | Acumulado de equilibrio |
|---|---|---|---|---|
| Baloto | $6.000 | $1.544 (26 %) | $596 (10 %) | ~$106 mil millones* |
| Revancha | $3.000 | $535 (18 %) | $299 (10 %) | ~$52 mil millones* |
| MiLoto | $4.000 | $1.706 (43 %) | $1.133 (28 %) | ~$2,5 mil millones* |
| ColorLoto | $5.000 | $1.437 (29 %) | $1.092 (22 %) | ~$26 mil millones* |

\* Muy por encima de los acumulados observados en el año (Baloto: máximo $62 mil millones): son
extrapolaciones que suponen que las ventas siguen creciendo con el premio de forma lineal.

Método: VE = Σ P(categoría) × premio promedio pagado (neto de la retención del 20 % sobre premios
> 48 UVT) + P(premio mayor) × acumulado neto × (1 − e^{−λ})/λ, con λ = ventas estimadas × P(premio
mayor). Las ventas se modelan como una recta en función del acumulado.

## Cuántas jugadas se venden

Mediana por sorteo: Baloto ~291.000, Revancha ~276.000, MiLoto ~93.000, ColorLoto ~10.000.
Estimadas como ganadores de una categoría / su probabilidad. En Baloto y Revancha la fila
"0 + SB" agrupa 0 y 1 aciertos con superbalota: con esa lectura, la estimación coincide con la de
otras categorías (291.000 vs 266.000 y 275.000); si fuera solo 0 aciertos daría 505.000, que no cuadra.

Con ~290.000 jugadas, si alguien acierta el premio mayor de Baloto la probabilidad de que otra
persona también lo acierte es de ~1,7 %. Por eso una jugada anti-popular apenas sube el VE ($1.548
vs $1.544): el reparto casi nunca ocurre.

## La gente sí juega fechas

Ganadores reales de 3–4 aciertos frente a los esperados si todos jugaran al azar, según cuántos
de los 5 números ganadores eran ≤ 31:

| ≤ 31 en el resultado | Sorteos | Reales / esperados (Baloto) |
|---|---|---|
| 0–1 | 5 | 0,70–0,85 |
| 2 | 13 | 0,76 |
| 3 | 42 | 0,90 |
| 4 | 57 | 1,06 |
| 5 | 39 | 1,28 |

Spearman ρ = 0,51, p < 0,001 (Revancha: ρ = 0,33, p < 0,001). Cuando salen fechas hay ~28 % más
ganadores de los esperados: evidencia directa, con datos reales, de lo que asume el puntaje de
popularidad del generador.

## Potencia: qué tan fuerte es el "no hay ventaja"

| Juego | Sorteos | Sesgo mínimo detectable de una balota (80 %) | Mejora mínima detectable en el backtest (80 %, Bonferroni 60) |
|---|---|---|---|
| Baloto | 650 | +57 % | +20 % de aciertos |
| MiLoto | 635 | +54 % | +19 % |
| ColorLoto | 231 | +85 % | +33 % |

Lectura: con los datos actuales descartamos sesgos grandes (una balota que salga 1,5 veces más de
lo normal) y estrategias que acierten un 20 % más que el azar. Sesgos más pequeños no se pueden
descartar con 650 sorteos; para detectar +20 % en una balota harían falta varios miles. Ambas
fórmulas se validaron por simulación (`tests/test_power.py`).
