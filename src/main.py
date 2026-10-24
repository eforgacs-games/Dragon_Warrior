#!/usr/bin/env python
from src.config.prod_config import prod_config
# This file is mainly here for the repl.it
from src.crash_log import install as install_crash_log
from src.game import Game


def run():  # pragma: no cover
    install_crash_log()
    game = Game(prod_config)
    game.main()


if __name__ == "__main__":
    run()
