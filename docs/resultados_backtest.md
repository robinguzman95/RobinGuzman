# Resultados del backtest

Generado el 2026-11-04 con `uv run lotolab backtest-all`.

**Pregunta:** ¿alguna estrategia popular acierta más que una jugada al azar?

**Método:** ventana móvil sin mirar al futuro (para el sorteo t solo se usan sorteos anteriores a t); línea base de 10.000 jugadas aleatorias (Monte Carlo hipergeométrico) sobre los mismos sorteos; p-valor de una cola; ventana principal **100** sorteos, declarada antes de correr; 50, 200 son de sensibilidad. Corrección de Bonferroni sobre las 60 combinaciones: α = 0,05 / 60 = 0,00083.

## Veredicto

**Ninguna estrategia le gana al azar.** Tras la corrección por comparaciones múltiples, ninguna combinación acierta más de lo que produciría jugar al azar, como se espera si los sorteos son independientes.

Sin corregir (p < 0,05 y sobre p95) salen 1 de 60 combinaciones; solo por azar se esperan unas 3,0. Por eso hace falta Bonferroni: al probar muchas estrategias a la vez, alguna "gana" por suerte. Casos: ColorLoto · overdue · ventana 100 (p = 0,031).

## Ventana principal

| Juego | Estrategia | Ventana | Sorteos evaluados | Aciertos/sorteo | Banda azar p5–p95 | p-valor | Resultado | Prob. premio mayor |
|---|---|---|---|---|---|---|---|---|
| Baloto | random | 100 | 550 (2022-04-16 → 2026-11-02) | 0,569 | 0,535–0,629 | 0,679 | dentro de la banda | 1 en 15.401.568 |
| Baloto | hot | 100 | 550 (2022-04-16 → 2026-11-02) | 0,547 | 0,535–0,629 | 0,890 | dentro de la banda | 1 en 15.401.568 |
| Baloto | cold | 100 | 550 (2022-04-16 → 2026-11-02) | 0,564 | 0,535–0,629 | 0,747 | dentro de la banda | 1 en 15.401.568 |
| Baloto | overdue | 100 | 550 (2022-04-16 → 2026-11-02) | 0,593 | 0,535–0,629 | 0,360 | dentro de la banda | 1 en 15.401.568 |
| Baloto | anti_popular | 100 | 550 (2022-04-16 → 2026-11-02) | 0,582 | 0,535–0,629 | 0,507 | dentro de la banda | 1 en 15.401.568 |
| Revancha | random | 100 | 550 (2022-04-16 → 2026-11-02) | 0,565 | 0,535–0,629 | 0,725 | dentro de la banda | 1 en 15.401.568 |
| Revancha | hot | 100 | 550 (2022-04-16 → 2026-11-02) | 0,575 | 0,535–0,629 | 0,607 | dentro de la banda | 1 en 15.401.568 |
| Revancha | cold | 100 | 550 (2022-04-16 → 2026-11-02) | 0,573 | 0,535–0,629 | 0,633 | dentro de la banda | 1 en 15.401.568 |
| Revancha | overdue | 100 | 550 (2022-04-16 → 2026-11-02) | 0,582 | 0,535–0,629 | 0,507 | dentro de la banda | 1 en 15.401.568 |
| Revancha | anti_popular | 100 | 550 (2022-04-16 → 2026-11-02) | 0,540 | 0,535–0,629 | 0,934 | dentro de la banda | 1 en 15.401.568 |
| MiLoto | random | 100 | 535 (2024-04-12 → 2026-11-03) | 0,622 | 0,591–0,692 | 0,734 | dentro de la banda | 1 en 575.757 |
| MiLoto | hot | 100 | 535 (2024-04-12 → 2026-11-03) | 0,589 | 0,591–0,692 | 0,962 | dentro de la banda | 1 en 575.757 |
| MiLoto | cold | 100 | 535 (2024-04-12 → 2026-11-03) | 0,643 | 0,591–0,692 | 0,487 | dentro de la banda | 1 en 575.757 |
| MiLoto | overdue | 100 | 535 (2024-04-12 → 2026-11-03) | 0,645 | 0,591–0,692 | 0,464 | dentro de la banda | 1 en 575.757 |
| MiLoto | anti_popular | 100 | 535 (2024-04-12 → 2026-11-03) | 0,652 | 0,591–0,692 | 0,371 | dentro de la banda | 1 en 575.757 |
| ColorLoto | random | 100 | 131 (2025-07-31 → 2026-11-02) | 0,809 | 0,740–0,977 | 0,769 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | hot | 100 | 131 (2025-07-31 → 2026-11-02) | 0,863 | 0,740–0,977 | 0,488 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | cold | 100 | 131 (2025-07-31 → 2026-11-02) | 0,901 | 0,740–0,977 | 0,288 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | overdue | 100 | 131 (2025-07-31 → 2026-11-02) | 0,992 | 0,740–0,977 | 0,031 | sobre p95, pero no significativo tras Bonferroni | 1 en 5.245.786 |
| ColorLoto | anti_popular | 100 | 131 (2025-07-31 → 2026-11-02) | 0,908 | 0,740–0,977 | 0,251 | dentro de la banda | 1 en 5.245.786 |

## Sensibilidad (otras ventanas)

| Juego | Estrategia | Ventana | Sorteos evaluados | Aciertos/sorteo | Banda azar p5–p95 | p-valor | Resultado | Prob. premio mayor |
|---|---|---|---|---|---|---|---|---|
| Baloto | random | 50 | 600 (2021-10-23 → 2026-11-02) | 0,563 | 0,537–0,628 | 0,751 | dentro de la banda | 1 en 15.401.568 |
| Baloto | hot | 50 | 600 (2021-10-23 → 2026-11-02) | 0,552 | 0,537–0,628 | 0,866 | dentro de la banda | 1 en 15.401.568 |
| Baloto | cold | 50 | 600 (2021-10-23 → 2026-11-02) | 0,563 | 0,537–0,628 | 0,751 | dentro de la banda | 1 en 15.401.568 |
| Baloto | overdue | 50 | 600 (2021-10-23 → 2026-11-02) | 0,588 | 0,537–0,628 | 0,419 | dentro de la banda | 1 en 15.401.568 |
| Baloto | anti_popular | 50 | 600 (2021-10-23 → 2026-11-02) | 0,582 | 0,537–0,628 | 0,513 | dentro de la banda | 1 en 15.401.568 |
| Baloto | random | 200 | 450 (2023-04-01 → 2026-11-02) | 0,567 | 0,529–0,636 | 0,689 | dentro de la banda | 1 en 15.401.568 |
| Baloto | hot | 200 | 450 (2023-04-01 → 2026-11-02) | 0,600 | 0,529–0,636 | 0,294 | dentro de la banda | 1 en 15.401.568 |
| Baloto | cold | 200 | 450 (2023-04-01 → 2026-11-02) | 0,578 | 0,529–0,636 | 0,552 | dentro de la banda | 1 en 15.401.568 |
| Baloto | overdue | 200 | 450 (2023-04-01 → 2026-11-02) | 0,571 | 0,529–0,636 | 0,640 | dentro de la banda | 1 en 15.401.568 |
| Baloto | anti_popular | 200 | 450 (2023-04-01 → 2026-11-02) | 0,560 | 0,529–0,636 | 0,762 | dentro de la banda | 1 en 15.401.568 |
| Revancha | random | 50 | 600 (2021-10-23 → 2026-11-02) | 0,563 | 0,537–0,628 | 0,751 | dentro de la banda | 1 en 15.401.568 |
| Revancha | hot | 50 | 600 (2021-10-23 → 2026-11-02) | 0,572 | 0,537–0,628 | 0,652 | dentro de la banda | 1 en 15.401.568 |
| Revancha | cold | 50 | 600 (2021-10-23 → 2026-11-02) | 0,532 | 0,537–0,628 | 0,968 | dentro de la banda | 1 en 15.401.568 |
| Revancha | overdue | 50 | 600 (2021-10-23 → 2026-11-02) | 0,588 | 0,537–0,628 | 0,419 | dentro de la banda | 1 en 15.401.568 |
| Revancha | anti_popular | 50 | 600 (2021-10-23 → 2026-11-02) | 0,537 | 0,537–0,628 | 0,953 | dentro de la banda | 1 en 15.401.568 |
| Revancha | random | 200 | 450 (2023-04-01 → 2026-11-02) | 0,538 | 0,529–0,636 | 0,919 | dentro de la banda | 1 en 15.401.568 |
| Revancha | hot | 200 | 450 (2023-04-01 → 2026-11-02) | 0,562 | 0,529–0,636 | 0,738 | dentro de la banda | 1 en 15.401.568 |
| Revancha | cold | 200 | 450 (2023-04-01 → 2026-11-02) | 0,589 | 0,529–0,636 | 0,415 | dentro de la banda | 1 en 15.401.568 |
| Revancha | overdue | 200 | 450 (2023-04-01 → 2026-11-02) | 0,580 | 0,529–0,636 | 0,525 | dentro de la banda | 1 en 15.401.568 |
| Revancha | anti_popular | 200 | 450 (2023-04-01 → 2026-11-02) | 0,513 | 0,529–0,636 | 0,986 | dentro de la banda | 1 en 15.401.568 |
| MiLoto | random | 50 | 585 (2024-01-16 → 2026-11-03) | 0,641 | 0,593–0,691 | 0,515 | dentro de la banda | 1 en 575.757 |
| MiLoto | hot | 50 | 585 (2024-01-16 → 2026-11-03) | 0,562 | 0,593–0,691 | 0,997 | dentro de la banda | 1 en 575.757 |
| MiLoto | cold | 50 | 585 (2024-01-16 → 2026-11-03) | 0,650 | 0,593–0,691 | 0,401 | dentro de la banda | 1 en 575.757 |
| MiLoto | overdue | 50 | 585 (2024-01-16 → 2026-11-03) | 0,668 | 0,593–0,691 | 0,187 | dentro de la banda | 1 en 575.757 |
| MiLoto | anti_popular | 50 | 585 (2024-01-16 → 2026-11-03) | 0,656 | 0,593–0,691 | 0,314 | dentro de la banda | 1 en 575.757 |
| MiLoto | random | 200 | 435 (2024-10-04 → 2026-11-03) | 0,641 | 0,586–0,697 | 0,508 | dentro de la banda | 1 en 575.757 |
| MiLoto | hot | 200 | 435 (2024-10-04 → 2026-11-03) | 0,591 | 0,586–0,697 | 0,938 | dentro de la banda | 1 en 575.757 |
| MiLoto | cold | 200 | 435 (2024-10-04 → 2026-11-03) | 0,660 | 0,586–0,697 | 0,305 | dentro de la banda | 1 en 575.757 |
| MiLoto | overdue | 200 | 435 (2024-10-04 → 2026-11-03) | 0,641 | 0,586–0,697 | 0,508 | dentro de la banda | 1 en 575.757 |
| MiLoto | anti_popular | 200 | 435 (2024-10-04 → 2026-11-03) | 0,657 | 0,586–0,697 | 0,328 | dentro de la banda | 1 en 575.757 |
| ColorLoto | random | 50 | 181 (2025-02-06 → 2026-11-02) | 0,834 | 0,762–0,956 | 0,660 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | hot | 50 | 181 (2025-02-06 → 2026-11-02) | 0,912 | 0,762–0,956 | 0,194 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | cold | 50 | 181 (2025-02-06 → 2026-11-02) | 0,928 | 0,762–0,956 | 0,127 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | overdue | 50 | 181 (2025-02-06 → 2026-11-02) | 0,950 | 0,762–0,956 | 0,067 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | anti_popular | 50 | 181 (2025-02-06 → 2026-11-02) | 0,845 | 0,762–0,956 | 0,590 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | random | 200 | 31 (2026-07-16 → 2026-11-02) | 0,806 | 0,613–1,097 | 0,674 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | hot | 200 | 31 (2026-07-16 → 2026-11-02) | 0,645 | 0,613–1,097 | 0,945 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | cold | 200 | 31 (2026-07-16 → 2026-11-02) | 1,032 | 0,613–1,097 | 0,133 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | overdue | 200 | 31 (2026-07-16 → 2026-11-02) | 0,935 | 0,613–1,097 | 0,326 | dentro de la banda | 1 en 5.245.786 |
| ColorLoto | anti_popular | 200 | 31 (2026-07-16 → 2026-11-02) | 0,742 | 0,613–1,097 | 0,815 | dentro de la banda | 1 en 5.245.786 |

## Cómo leer la tabla

- **Aciertos/sorteo:** promedio de números principales acertados por sorteo evaluado.
- **Banda p5–p95:** el 90% central de los promedios de 10.000 jugadas aleatorias en el mismo periodo.
- **p-valor:** proporción de jugadas aleatorias que igualan o superan a la estrategia.
- La probabilidad real del premio mayor no cambia con ninguna estrategia.
