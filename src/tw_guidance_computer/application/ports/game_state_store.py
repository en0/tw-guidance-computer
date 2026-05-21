"""Combined port for persistent game state storage."""

from typing import Protocol

from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.application.ports.game_state_writer import GameStateWriter


class GameStateStore(GameStateReader, GameStateWriter, Protocol):
    """Combined read/write port for persistent game state storage.

    This exists for the composition root and adapter inheritance.
    Use cases should depend on GameStateReader or GameStateWriter
    individually to make their dependency contracts visible.
    """

    ...
