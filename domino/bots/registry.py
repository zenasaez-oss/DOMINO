"""Finds every bot automatically: adding a bot = adding a file to domino/bots/.

Any class in a module of the domino.bots package that inherits from Bot is a bot. Nobody keeps a
list by hand, so a bot sent by another team is found as soon as its file is in the folder.

    from domino.bots import find_bots
    find_bots()     # {"Greedy": GreedyBot, "Scoring": ScoringBot, ...}

Problems are reported, not hidden:
    - a file that fails to import (e.g. a syntax error),
    - an incomplete bot (it forgot one of the required methods),
    - two bots with the same name.
find_bots() raises BotRegistryError listing all of them; scan() returns them instead, so a
tournament can skip the broken ones and still run.
"""
import importlib
import inspect
import pkgutil

from .base import Bot

NOT_BOTS = {"base", "registry"}   # modules of the package that hold no bots


class BotRegistryError(Exception):
    """Something is wrong with one or more bot files. The message lists every problem."""


def scan(package="domino.bots"):
    """Look through every module of `package`. Returns (bots, problems):
    bots is {name: class}, problems a list of sentences describing what's wrong."""
    root = importlib.import_module(package)
    bots, problems = {}, []
    for info in sorted(pkgutil.iter_modules(root.__path__), key=lambda m: m.name):
        if info.name in NOT_BOTS or info.name.startswith("_"):
            continue
        module_name = f"{package}.{info.name}"
        try:
            module = importlib.import_module(module_name)
        except Exception as error:   # noqa: BLE001 - a broken file must not hide the others
            problems.append(f"{module_name} can't be imported: {type(error).__name__}: {error}")
            continue
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if not issubclass(cls, Bot) or cls is Bot or cls.__module__ != module_name:
                continue
            if inspect.isabstract(cls):
                missing = ", ".join(sorted(cls.__abstractmethods__))
                problems.append(f"{cls.__name__} ({module_name}) is incomplete: it doesn't write {missing}")
                continue
            try:
                name = cls.get_name()
            except Exception as error:   # noqa: BLE001
                problems.append(f"{cls.__name__} ({module_name}): get_name() failed: {error}")
                continue
            if not isinstance(name, str) or not name.strip():
                problems.append(f"{cls.__name__} ({module_name}): get_name() must return a non-empty text")
            elif name in bots:
                problems.append(f"two bots are called {name!r}: {bots[name].__name__} and {cls.__name__}")
            else:
                bots[name] = cls
    return bots, problems


def find_bots(package="domino.bots"):
    """{name: bot class} for every bot in `package`. Raises BotRegistryError if anything is wrong."""
    bots, problems = scan(package)
    if problems:
        raise BotRegistryError("\n".join(problems))
    return bots


def describe(bot_class):
    """Who a bot is, as plain data for pages and tables: {"name", "authors", "description"}."""
    authors = bot_class.get_authors()
    if isinstance(authors, str):      # one author written without the list
        authors = [authors]
    return {"name": bot_class.get_name(), "authors": [str(a) for a in authors],
            "description": str(bot_class.get_description())}
