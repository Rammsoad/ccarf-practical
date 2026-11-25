# Grabaciones

Corridas guardadas para verlas sin gastar: en el panel salen como **▶ grabada** junto a su caso, y sin Python en
`grabaciones/reproductor.html`. No gastan tokens ni necesitan key.

- Una carpeta por demo. Cada grabación son dos archivos: `.json` (la salida, con sus tiempos) y `.html` (la página
  con el diagrama).
- **Todas son reales** (corridas con Haiku 5.5, noviembre de 2026): 1.1 (los cuatro casos), 1.2, 1.3 (parte C),
  2.2 (los dos casos), 2.3 (documento desconocido), 2.5, 3.1, 3.4, 3.5 (TDD y solo prosa), 4.3 (los dos casos), 4.4,
  5.1 (los dos casos de la parte A) y 5.2 (comparación).
- **En inglés:** cada grabación tiene su versión en `en/` (mismo nombre de archivo), corrida con el panel en inglés.
  El panel muestra la del idioma elegido.
- 1.4 y 1.5 ❌ no tienen grabación: en 3 intentos el modelo se frenó solo (no se saltó la regla), así que no se ve
  la falla. En el examen la respuesta sigue siendo la misma: la regla va en código.
- Para agregar las tuyas: corre una demo en el panel con tu key y, al terminar, dale **Guardar como grabación**.
  Las rutas de tu computadora se quitan solas al guardar.
- Para quitar una, borra sus dos archivos. Después corre `python paginas.py` para actualizar el reproductor.
