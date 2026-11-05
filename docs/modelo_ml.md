# Modelo de machine learning (Fase 7)

**Pregunta:** ¿un modelo que aprende de la historia de cada balota estima su probabilidad de salir
mejor que "todas tienen la misma"?

## Método

- **Unidad:** cada balota en cada sorteo (Baloto 43, MiLoto 39, ColorLoto 42 pares número-color;
  superbalota 16 por separado). Objetivo: 1 si salió, 0 si no.
- **Variables** (solo con sorteos anteriores): frecuencia en los últimos 10, 25, 50 y 100 sorteos,
  frecuencia total, log(1 + sorteos sin salir) y si salió en el sorteo anterior.
- **Modelos:** gradient boosting (`HistGradientBoostingClassifier` de scikit-learn, el mismo tipo
  de modelo que LightGBM) y regresión logística.
- **Evaluación walk-forward:** la segunda mitad de los sorteos es la prueba. Cada 25 sorteos el
  modelo se reentrena con todo lo anterior y predice los 25 siguientes. Nunca ve el sorteo que
  predice (prueba `test_features_never_use_the_predicted_draw_or_later`, que de hecho detectó y
  corrigió una fuga en el valor inicial de las variables).
- **Métricas:** log-loss y Brier frente a la probabilidad constante K/B; habilidad = 1 − LL/LL_azar
  con IC 95 % por bootstrap; aciertos de las K balotas más probables frente a 10.000 jugadas al azar.

## Control: ¿el modelo es capaz de aprender?

En sorteos simulados con un patrón escondido (una balota que salió tiende a repetir con
probabilidad 0,5), ambos modelos lo aprenden: habilidad > 5 %, IC por encima de 0 y aciertos por
encima del p95 del azar (`test_learns_a_planted_pattern`). En sorteos simulados sin patrón no
"descubren" nada (`test_no_signal_means_no_skill`).

## Resultado con los sorteos reales

| Juego | Qué predice | Modelo | Habilidad | IC 95 % (mejora en log-loss) | Aciertos/sorteo | Azar (90 %) |
|---|---|---|---|---|---|---|
| Baloto | balotas | gradient boosting | −0,15 % | −0,0009 a −0,0002 | 0,498 | 0,520–0,643 |
| Baloto | balotas | logística | −0,07 % | −0,0005 a 0,0000 | 0,514 | 0,520–0,643 |
| Baloto | superbalota | gradient boosting | −2,90 % | −0,0104 a −0,0031 | 0,080 | 0,040–0,086 |
| MiLoto | balotas | logística | +0,02 % | −0,0003 a +0,0004 | 0,660 | 0,575–0,708 |
| ColorLoto | balotas | gradient boosting | −2,13 % | −0,0123 a −0,0050 | 0,888 | 0,733–0,983 |

(Tabla completa en `data/ml_eval.json`; se regenera con `uv run lotolab ml`.)

**Conclusión:** ningún modelo predice mejor que el azar. El más sofisticado (gradient boosting)
sale *peor*: aprende coincidencias del pasado que no se repiten (sobreajuste). El simple empata.
Como el control muestra que los modelos sí aprenden cuando hay patrón, la explicación es que en
los sorteos reales no hay patrón que aprender.

Las probabilidades del modelo para el próximo sorteo quedan entre ~10 % y ~12,5 % por balota en
Baloto, frente a 11,6 % del azar: diferencias del tamaño del ruido.
