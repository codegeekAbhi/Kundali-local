"""Optional chart interpretation. Chart calculations stay in kundli.py."""

import json
import os
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ENDPOINTS = {
    "ollama": "http://127.0.0.1:11434/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}
HOUSE_THEMES = (
    "identity and initiative", "resources and speech", "communication and effort",
    "home and family", "creativity and learning", "routines and obligations",
    "partnerships", "shared resources and change", "beliefs and higher learning",
    "career and public responsibilities", "networks and gains", "retreat and expenses",
)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def offline_reading(ascendant, moon, moon_house, period, occupants, lal_kitab, topic):
    lines = [
        f"{ascendant} rising is the starting point for the whole-sign chart.",
        f"The Moon in {moon} places the emphasis on {HOUSE_THEMES[moon_house - 1]}.",
        f"The calculated timing sequence is {period}.",
    ]
    focus_house = {"career": 10, "relationships": 7}.get(topic)
    if focus_house:
        planets = ", ".join(occupants[focus_house - 1]) or "no natal planets"
        lines.append(f"For {topic}, start with house {focus_house}, which contains {planets}.")
    if lal_kitab:
        for house, planets in enumerate(occupants, start=1):
            if planets:
                lines.append(
                    f"Lal Kitab reading input — house {house} ({HOUSE_THEMES[house - 1]}): "
                    f"{', '.join(planets)}."
                )
    lines.append("These are traditional themes for reflection. Hiring dates and other outcomes are uncertain.")
    return "\n".join(lines)


def ai_reading(mode, model, topic, chart, lal_kitab):
    headers = {"Content-Type": "application/json"}
    body = {"model": model, "messages": [
        {"role": "system", "content": (
            "Write a concise traditional astrology interpretation using only these calculated "
            "chart facts. Preserve placements and dates. State when information is missing. "
            "Avoid guarantees, exact hiring predictions, and medical, legal or financial advice. "
            "If asked for Lal Kitab, label it as a separate house-based reading and do not "
            "invent Lal Kitab dasha, varshphal or remedy results."
        )},
        {"role": "user", "content": (
            f"Topic: {topic}. Lal Kitab house reading requested: {lal_kitab}.\n\n{chart}"
        )},
    ]}
    if mode == "openai":
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise ValueError("Set OPENAI_API_KEY to use OpenAI mode.")
        headers["Authorization"] = f"Bearer {key}"
        body["store"] = False
    request = Request(ENDPOINTS[mode], json.dumps(body).encode(), headers, method="POST")
    try:
        # Direct connections keep local model traffic off environment-configured proxies.
        opener = build_opener(ProxyHandler({}), NoRedirects())
        with opener.open(request, timeout=120) as response:
            answer = json.load(response)["choices"][0]["message"]["content"]
    except (URLError, OSError, ValueError, KeyError, IndexError, TypeError) as error:
        status = getattr(error, "code", None)
        detail = f" (HTTP {status})" if status else ""
        raise ValueError(f"{mode} could not return a reading{detail}.") from error
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"{mode} returned an empty reading.")
    return answer.strip()
