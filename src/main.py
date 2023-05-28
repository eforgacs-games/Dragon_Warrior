#!/usr/bin/env python
from src.config import prod_config
# This file is mainly here for the repl.it
from src.game import Game


def run():  # pragma: no cover
    game = Game(prod_config)
    game.main()


if __name__ == "__main__":
    run()
