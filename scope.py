"""
Which posts count as "about the Starlink connection"?

Used by collector.py, app.py and evaluate.py so all three agree.

A post is IN SCOPE when it mentions the connection experience (internet, outage,
speed, dish ...) AND does not mention politics, war or space news. We added the
second rule after reading our first day of data: 86% of the posts that passed the
first rule alone were about Ukraine, Musk, Trump or rocket launches, not about
people's internet.
"""

import re

CONNECTION_WORDS = [
    "internet", "connection", "connected", "connectivity", "online", "offline",
    "outage", "outages", "down", "dropped", "dropping", "disconnect", "disconnected",
    "speed", "speeds", "slow", "mbps", "gbps", "latency", "ping", "lag", "buffering",
    "upload", "download", "bandwidth", "signal", "coverage", "service",
    "dish", "dishy", "router", "wifi", "wi-fi", "install", "installed", "installation",
    "obstruction", "obstructions", "roaming", "rural", "broadband",
    "subscription", "price", "bill", "data cap", "reliable", "reliability",
    "unreliable", "not working", "customer support",
]

# Posts mentioning any of these are about politics, war or space news instead.
OFF_TOPIC_WORDS = [
    "ukraine", "ukrainian", "ukrainians", "russia", "russian", "russians", "putin", "kremlin",
    "musk", "elon", "elmo", "trump", "maga", "doge", "nazi", "fascist",
    "military", "army", "soldier", "soldiers", "troops", "war", "drone", "drones", "frontline",
    "pentagon", "nato", "iran", "israel", "gaza", "china", "chinese", "taiwan",
    "spacex", "tesla", "launch", "launches", "launched", "falcon", "rocket", "booster",
    "orbit", "satellites", "constellation", "tariff", "tariffs", "contract", "contracts",
]


def _word_regex(words):
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE)


_CONNECTION_RE = _word_regex(CONNECTION_WORDS)
_OFF_TOPIC_RE = _word_regex(OFF_TOPIC_WORDS)


def is_in_scope(text) -> bool:
    text = str(text)
    return bool(_CONNECTION_RE.search(text)) and not _OFF_TOPIC_RE.search(text)
