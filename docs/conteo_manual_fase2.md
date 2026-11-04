# Conteo manual — criterio de salida de la Fase 2

> "Pasa cuando: los números cuadran con un conteo manual de 10 sorteos." — Plan Técnico

Los conteos de abajo se hicieron a mano a partir de `data/raw/*.csv` y están escritos como
valores literales en `backend/tests/test_frequency.py`. Si `app/analysis/frequency.py` no da
exactamente lo mismo, la prueba falla. Verifícalos con lápiz y papel.

## Baloto — sorteos 2721 a 2730 (12 oct – 2 nov 2026)

| Sorteo | Fecha | Números | Superbalota |
|---|---|---|---|
| 2721 | 2026-10-12 | 8 · 13 · 25 · 33 · 41 | 12 |
| 2722 | 2026-10-14 | 5 · 6 · 7 · 19 · 40 | 3 |
| 2723 | 2026-10-17 | 6 · 9 · 12 · 26 · 29 | 9 |
| 2724 | 2026-10-19 | 6 · 19 · 20 · 25 · 28 | 4 |
| 2725 | 2026-10-21 | 4 · 6 · 28 · 30 · 38 | 16 |
| 2726 | 2026-10-24 | 11 · 13 · 15 · 29 · 41 | 8 |
| 2727 | 2026-10-26 | 17 · 25 · 30 · 33 · 35 | 7 |
| 2728 | 2026-10-28 | 11 · 23 · 29 · 36 · 43 | 16 |
| 2729 | 2026-10-31 | 10 · 19 · 21 · 29 · 39 | 12 |
| 2730 | 2026-11-02 | 18 · 19 · 20 · 31 · 43 | 14 |

**Frecuencia de números (50 balotas):**

| Veces | Números |
|---|---|
| 4 | 6, 19, 29 |
| 3 | 25 |
| 2 | 11, 13, 20, 28, 30, 33, 41, 43 |
| 1 | 4, 5, 7, 8, 9, 10, 12, 15, 17, 18, 21, 23, 26, 31, 35, 36, 38, 39, 40 |
| 0 | 1, 2, 3, 14, 16, 22, 24, 27, 32, 34, 37, 42 |

Comprobación: 3·4 + 1·3 + 8·2 + 19·1 = 50 ✓ · 3 + 1 + 8 + 19 + 12 = 43 números ✓

**Superbalota:** 12 y 16 salieron 2 veces; 3, 4, 7, 8, 9 y 14 una vez (total 10 ✓).

**Pares que salieron juntos dos veces** (ningún par salió 3 veces, ningún trío se repitió):
(6, 19) en 2722 y 2724 · (6, 28) en 2724 y 2725 · (11, 29) en 2726 y 2728 ·
(13, 41) en 2721 y 2726 · (19, 20) en 2724 y 2730 · (25, 33) en 2721 y 2727.

**Calientes con desempate por recencia:** 19 (salió en el último sorteo), 29 (hace 1),
6 (hace 5), luego 25 (3 veces).

**Último sorteo (2730):** suma 131; 2 pares (18, 20); 2 altos > 21,5 (31, 43).

## MiLoto — sorteos 626 a 635 (19 oct – 3 nov 2026)

| Sorteo | Fecha | Números |
|---|---|---|
| 626 | 2026-10-19 | 1 · 10 · 11 · 27 · 28 |
| 627 | 2026-10-20 | 12 · 13 · 14 · 33 · 36 |
| 628 | 2026-10-22 | 15 · 16 · 18 · 28 · 37 |
| 629 | 2026-10-23 | 1 · 6 · 11 · 35 · 37 |
| 630 | 2026-10-26 | 1 · 10 · 12 · 14 · 36 |
| 631 | 2026-10-27 | 14 · 19 · 21 · 23 · 34 |
| 632 | 2026-10-29 | 5 · 8 · 14 · 23 · 37 |
| 633 | 2026-10-30 | 12 · 18 · 26 · 27 · 34 |
| 634 | 2026-11-02 | 4 · 26 · 29 · 34 · 35 |
| 635 | 2026-11-03 | 8 · 13 · 20 · 24 · 25 |

| Veces | Números |
|---|---|
| 4 | 14 |
| 3 | 1, 12, 34, 37 |
| 2 | 8, 10, 11, 13, 18, 23, 26, 27, 28, 35, 36 |
| 1 | 4, 5, 6, 15, 16, 19, 20, 21, 24, 25, 29, 33 |
| 0 | 2, 3, 7, 9, 17, 22, 30, 31, 32, 38, 39 |

Comprobación: 4 + 4·3 + 11·2 + 12·1 = 50 ✓ · 1 + 4 + 11 + 12 + 11 = 39 números ✓

## Notas de método

- **Chi-cuadrado corregido.** En cada sorteo salen K balotas distintas de N, así que las cuentas
  no son multinomiales. El estadístico de Pearson se divide por c = (N−K)/(N−1) (38/42 en
  Baloto) para que siga χ²(N−1). Una simulación de 400 historiales aleatorios en las pruebas
  confirma que así se rechaza ~5% de las veces, como debe ser.
- **Rachas con p-valor exacto.** La aproximación normal de Wald–Wolfowitz falla cuando una balota
  sale pocas veces. En el histórico real, 7-blanco de ColorLoto (17 apariciones en 113 sorteos,
  con una racha de 5 sorteos seguidos, del 192 al 196) daba p = 0,0009 con la normal, por debajo
  del umbral de Bonferroni 0,05/42 = 0,0012. Con la distribución exacta da p = 0,0055: **no es
  atípica**. Una racha de 5 o más aparece en alguna de las 42 balotas en ~21% de los
  historiales simulados de 113 sorteos (5.000 simulaciones, semilla 42): 1 de cada 5.

## Resultado sobre el histórico completo (oct 2025 – nov 2026)

| Juego | Sorteos | Chi-cuadrado números | Rachas (Bonferroni) |
|---|---|---|---|
| Baloto | 171 | p = 0,35 · compatible con el azar | ninguna atípica |
| Revancha | 171 | p = 0,70 · compatible con el azar | ninguna atípica |
| MiLoto | 229 | p = 0,91 · compatible con el azar | ninguna atípica |
| ColorLoto | 113 | balotas p = 0,83 · números p = 0,88 · colores p = 0,53 | ninguna atípica |
