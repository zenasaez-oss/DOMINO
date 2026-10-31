# Cómo contribuir con un bot

¿Quieres que tu bot juegue en nuestro Dominó, en el ranking y en el torneo? Es un único archivo nuevo.

1. **Haz un fork** de https://github.com/zenasaez-oss/DOMINO y crea una rama (`git switch -c mi-bot`).
2. **Crea tu bot** en `domino/bots/<tu_equipo>.py`: una clase que herede de `Bot` con
   `get_name`, `get_authors`, `get_description` y `choose(view, moves)`.
3. **Pruébalo**: `python -m unittest discover -s tests -t .` debe acabar en `OK`.
4. **Abre una pull request** hacia `main` de este repositorio.

Guía paso a paso con ejemplos: [tutorial](docs/tutorial.md) · Qué ve y devuelve un bot: [contrato](docs/contract.md).

## Reglas para que se acepte

- Un solo archivo nuevo en `domino/bots/`; no se modifica el motor, otros bots ni los tests.
- Nombre único, al menos un autor y una descripción de la estrategia.
- `choose` devuelve exactamente uno de `moves`, tal cual.
- Solo biblioteca estándar de Python (la web ejecuta los bots en el navegador).
- Sin imprimir, sin archivos, sin red.
- Máximo 5 segundos por jugada.
- El bot solo usa lo que ve en `view`: no mira la mano del rival.
- Código propio: no se aceptan bots copiados de otros repositorios.

## Qué pasa después

Los tests se ejecutan automáticamente en tu PR. Con tick verde, un miembro del equipo la revisa y la
integra; desde ese momento tu bot aparece en el arena, el ranking y el torneo.
