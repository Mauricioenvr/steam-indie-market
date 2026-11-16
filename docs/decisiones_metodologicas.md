# Decisiones metodológicas

Registro de las decisiones de diseño del análisis y de su justificación.
Se actualiza a medida que avanza el proyecto.

## 1. Cómo se mide el "éxito"

Steam no publica ventas, así que el éxito se mide con señales aproximadas.
Se usan **dos dimensiones separadas** en lugar de una sola métrica:

| Dimensión | Métrica principal | Qué mide |
|---|---|---|
| Alcance comercial | Volumen total de reseñas (`positive + negative`), en escala log | Cuántos jugadores compraron o jugaron el juego |
| Calidad percibida | % de reseñas positivas, ajustado por confianza | Qué tan satisfechos quedaron |

**Por qué el volumen y no solo la valoración:** solo los dueños de un juego pueden
reseñarlo, y cada reseña (positiva o negativa) corresponde a una compra ya realizada.
Un juego con muchas reseñas negativas probablemente vendió más que uno con pocas
reseñas positivas. Sin embargo, una mala valoración tiende a frenar las ventas
**futuras** (etiqueta visible en la tienda y menos recomendaciones del algoritmo).

**Cuadrantes de resultado:** se cruzan ambas dimensiones:

| | Valoración alta | Valoración baja |
|---|---|---|
| **Volumen alto** | Éxito pleno | Éxito comercial polémico |
| **Volumen bajo** | Joya oculta | Fracaso |

Los umbrales se definirán con percentiles dentro de cada cohorte de año de
lanzamiento, para no comparar juegos con distinta antigüedad.

**Valoración ajustada por confianza:** un 100 % con 3 reseñas no equivale a un 95 %
con 5.000. Se usará la fórmula de SteamDB y/o el límite inferior de Wilson.

## 2. Ventas estimadas

La proporción de reseñas a ventas varía según el precio, el año y el género
(normalmente entre 1:30 y 1:60). Las ventas estimadas se presentan como **rangos**,
nunca como cifras exactas. Los rangos de propietarios de SteamSpy se usan como
segunda referencia.

## 3. Definición de "indie"

La etiqueta *Indie* la asigna el desarrollador (como género) o la comunidad
(como tag). Se guardan ambos indicadores por separado (`is_indie_genre`,
`is_indie_tag`).

**Criterio final: `is_indie = género Indie O tag Indie`** (103.234 juegos, 68,6 % del
catálogo, snapshot del 2026-11-13). Justificación:

| Género Indie | Tag Indie | Juegos | Mediana de reseñas |
|---|---|---|---|
| Sí | Sí | 46.182 | 23 |
| Sí | No | 54.600 | 0 |
| No | Sí | 2.452 | 42 |
| No | No | 47.232 | 0 |

- De los 54.600 juegos con género pero sin tag, 41.008 **no tienen ningún tag**:
  los tags los vota la comunidad y casi nadie los ha jugado. Usar solo el tag
  excluiría a los juegos con menos visibilidad y sesgaría el análisis hacia los exitosos.
- Los 2.452 juegos con tag pero sin género son juegos que la comunidad reconoce
  como indie aunque el desarrollador no lo haya declarado.

## 4. Inferencia, no causalidad

Las regresiones muestran **asociaciones**. Que una etiqueta se asocie con más
reseñas no significa que añadirla vaya a generar ventas, porque pueden influir
variables omitidas como el presupuesto de marketing o el tamaño del estudio.

## 5. Fuentes y cortes temporales

- **Base:** FronkonGames *Steam Games Dataset* (Kaggle / Hugging Face), formato JSON.
  Se evita el CSV porque tiene un error conocido en el encabezado
  (`DiscountDLC count`) que desplaza las columnas.
- **Enriquecimiento:** Steam Store API y SteamSpy, para actualizar métricas.
- Cada carga se guarda como un *snapshot* con fecha y fuente, para que los datos
  de Kaggle y de la API convivan sin sobrescribirse.
- El precio del dataset es el precio al momento del scraping (puede incluir
  descuentos activos), no necesariamente el precio de lanzamiento.
- Las versiones recientes del JSON traen `release_date` como texto (antes era un
  objeto) y ya no incluyen `is_free`, que se deriva como `price = 0`. El
  pipeline acepta ambos formatos.
- El campo `discount` llega con tipos mezclados (número, texto o nulo) y se
  normaliza a un porcentaje entero.

## 5b. Precio de lista

El snapshot (2026-11-13) coincidió con descuentos activos: Terraria aparece a
$4,99 con 50 % de descuento (precio de lista $9,99). Para el análisis de precios
se usa `list_price_usd = price / (1 − discount/100)`, ajustado al precio
terminado en ,99 más cercano cuando la diferencia es de 3 centavos o menos. Con
100 % de descuento no se puede reconstruir y queda NULL.

`is_free` y `price` reflejan el estado **actual**: Rocket League y Fall Guys
aparecen como gratuitos aunque se lanzaron con precio.

## 5c. Software excluido

El dataset incluye unos 4.000 productos que no son juegos (Wallpaper Engine,
herramientas de diseño, audio, desarrollo). `is_software` marca los que tienen un
género de software o multimedia (Utilities, Design & Illustration, Animation &
Modeling, Video Production, Game Development, Audio Production, Software
Training, Photo Editing, Web Publishing, Accounting, Movie, 360 Video, Tutorial,
Documentary, Short) y los que tienen *Education* sin ningún género de juego. Los
juegos educativos se conservan.

## 5d. Límite de la definición de indie

La etiqueta es autodeclarada: incluye estudios grandes como Facepunch (Rust),
Studio Wildcard (ARK) o estudios de Epic (Rocket League, Fall Guys). No existe un
criterio objetivo para excluirlos. Su peso en los análisis por cohorte es
mínimo, pero dominan los rankings absolutos.

## 6. Juegos publicados vs. anunciados

El dataset incluye juegos con fecha de lanzamiento posterior al snapshot
(lanzamientos programados). La vista principal `core.v_game_latest` incluye solo
juegos publicados (`release_date <= snapshot_date`). `core.v_game_all` los
conserva todos, con el indicador `is_released`.

## 7. Panorama inicial (snapshot 2026-11-13)

Cifras calculadas antes de excluir los lanzamientos futuros; se actualizarán.

- 150.466 juegos. Mediana de 2 reseñas frente a una media de 990: el éxito está
  extremadamente concentrado.
- El 44,8 % no tiene ninguna reseña y el 62,3 % tiene menos de 10.
- Los lanzamientos crecieron de 14.607 (2023) a 24.977 (2025).

## 8. Hallazgo: la atención del mercado es un "pastel fijo"

Entre 2016 y 2024 los lanzamientos indie se multiplicaron por 4,2 (de 3.078 a
12.921). Sin embargo, la cantidad de indies que alcanzan cada umbral de reseñas
casi no cambió:

| Umbral | Rango anual 2016–2024 |
|---|---|
| 100 o más reseñas | 1.186 – 1.611 |
| 1.000 o más reseñas | 329 – 441 |
| 10.000 o más reseñas | 53 – 80 |

La probabilidad de que un indie llegue a 100 reseñas cayó de 47,5 % (2016) a
12,5 % (2024). El crecimiento de lanzamientos aumentó sobre todo la cantidad
de juegos que pasan desapercibidos.

**Límites:** 2024 todavía está acumulando reseñas (su cifra puede crecer) y 2025
se excluye por ser demasiado reciente. Las reseñas son un proxy de ventas
(sección 1). Los juegos retirados de la tienda no aparecen (sesgo de
supervivencia). Es una descripción del mercado, no una relación causal.

## 9. Hallazgo: concentración extrema y creciente

Indies publicados antes de 2026 (83.055, antes de excluir software):

- El 1 % más reseñado acumula el 74,6 % de todas las reseñas; el 10 % superior,
  el 96 %; la mitad inferior, el 0,1 %.
- El coeficiente de Gini por cohorte subió de 0,85 (2013) a 0,96–0,97
  (2018–2024). El valor de 2025 (0,985) está inflado por la poca antigüedad.
- Es consistente con el hallazgo 8: si los lugares exitosos son casi constantes
  y compiten más juegos, la desigualdad aumenta.

## 10. Hallazgo: momento de lanzamiento (asociación, sin controles)

Indies 2016–2023, % que llega a 100 reseñas:

- **Mes:** de enero a mayo, entre 22,6 % y 23,9 %; noviembre y diciembre, 19,6 % y 19,2 %.
  Octubre y noviembre son además los meses con más lanzamientos por día.
- **Día:** jueves 25,9 % (el mejor), martes 24,0 % (el mejor en 1.000 o más reseñas),
  viernes 20,7 %, sábado y domingo entre 12 % y 13 %.
- **Posible confusión:** lanzar en fin de semana puede indicar un desarrollador sin
  publisher. La regresión incluirá una variable de autopublicado para separarlo.

## 11. Hallazgo: precio y éxito (asociación, sin controles)

Indies 2016–2023, precio de lista:

- **Oferta:** el 51 % se lanza a menos de $5 y solo el 2,8 % a $20 o más. La
  mediana del precio de los indies de pago se mantiene en ~$4,99 desde 2016, así que
  en términos reales (con inflación) ha bajado. La proporción de juegos gratuitos
  subió de 12,8 % a ~16 %.
- **Alcance:** el % que llega a 100 reseñas sube con el precio, de 12,7 % (< $2) a
  65,8 % ($20–29,99), y cae a 30,4 % en $30 o más. Ese tramo es bimodal: pocos
  éxitos grandes (22,5 % llega a 1.000) y muchos juegos sin tracción.
- **Calidad percibida:** la valoración mediana es casi plana (82–84 %) entre $2 y
  $30 o más; solo < $2 es más baja (78,4 %). Los jugadores no castigan el precio alto
  con peores reseñas.
- **Índice de ingresos** (reseñas × precio): los tramos de $15 a $29,99 (8,0 % de los
  indies de pago) concentran el 55 % del índice; los de menos de $5 (60 % de los
  juegos), solo el 2,4 %.

**Por qué no es causal:** (1) el precio refleja la ambición del juego: más
contenido, presupuesto y a veces publisher; (2) causalidad inversa: un juego que
no vende tiende a bajar su precio, y aquí se usa el precio actual; (3) el índice
supone que la proporción reseñas/ventas es igual en todos los tramos y que se vende
a precio de lista, cuando buena parte de las ventas ocurre con descuento.
