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
`is_indie_tag`) para medir cuánto difieren antes de fijar el criterio final.

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
