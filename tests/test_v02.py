"""Version 0.2: trailers, blurbs, the next showtimes, get_film's answer, and the list of films seen."""

from __future__ import annotations

from datetime import date, datetime, timezone
import sys
import types
from zoneinfo import ZoneInfo

import test_films as base
from fixtures import COWARD, SUDDEN, PRIMETIME, WILD_HORSE, SOON

films = base.films
AMS = ZoneInfo("Europe/Amsterdam")
FOUND = {f.id: f for f in films.now_showing(base.EVENTS, base.PRODS, base.NAMES, base.NOW, AMS)}


def test_trailer_is_served_as_mp4():
    assert FOUND[SUDDEN].trailer == ("https://culturekit-assets.imgix.net/1/assets/"
                                     "05c2f691-bce4-45e7-88ea-89eaec60aa65.mp4?fm=mp4")
    assert FOUND[COWARD].trailer is None


def test_plain_text_drops_markdown():
    assert films.plain_text("Van Hamaguchi (_Drive My Car_), **echt**  [hier](https://x.nl).") == \
        "Van Hamaguchi (Drive My Car), echt hier."


def test_lines_fit_a_screen_and_join_again():
    text = films.plain_text(FOUND[SUDDEN].description)
    lines = films.lines_of(text)
    assert "".join(lines) == text
    assert all(len(line.encode()) <= 44 for line in lines)
    assert len(lines) > 2
    long = "a" * 50 + " ééééééééééééééééééééééééééé"
    assert "".join(films.lines_of(long)) == long
    assert all(len(line.encode()) <= 44 for line in films.lines_of(long))


def test_showtimes_are_the_ones_still_to_come():
    coward = FOUND[COWARD]
    assert [v for _, v in coward.showtimes] == ["Kriterion", "Eye"]       # 11:00 at Cinecenter has begun
    assert coward.showtimes[0][0] == coward.next_start


def test_answer_of_get_film():
    answer = FOUND[SUDDEN].answer(AMS, seen=False, player="Woonkamer TV")
    assert answer["title"] == "All of a Sudden" and answer["highlight"] == "week"
    assert answer["blurb"].endswith("(Drive My Car).")
    assert "".join(answer["blurb_lines"]) == answer["blurb"]
    assert answer["has_trailer"] and answer["player"] == "Woonkamer TV"
    assert answer["shows"] == []                                          # today's only show began
    coward = FOUND[COWARD].answer(AMS, seen=True, player="")
    assert coward["seen"] and not coward["has_trailer"]
    assert coward["shows"][0] == {"at": int(datetime(2026, 10, 30, 18, 15, tzinfo=timezone.utc).timestamp()),
                                  "venue": "Kriterion"}
    assert len(answer) <= 24 and all(len(k) <= 32 for k in answer)        # what a Tessera answer keeps


def test_compact_has_ids():
    out = films.compact(list(FOUND.values()), "now", AMS)
    assert set(out["ids"]) == set(FOUND)


def test_coming_soon_has_its_previews():
    soon = films.coming_soon(SOON["_embedded"]["productions"], base.EVENTS, date(2026, 10, 30), 4, base.NAMES,
                             base.NOW)
    assert soon[0].id == WILD_HORSE and [v for _, v in soon[0].showtimes] == ["Kriterion"]


# ---- The list of films seen, with the little of Home Assistant it uses stood in ----

class FakeStore:
    saved = None

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        return FakeStore.saved

    def async_delay_save(self, data, delay):
        FakeStore.saved = data()


def _stub_homeassistant():
    ha = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.CALLBACK_TYPE = object
    core.HomeAssistant = object
    core.callback = lambda f: f
    helpers = types.ModuleType("homeassistant.helpers")
    storage = types.ModuleType("homeassistant.helpers.storage")
    storage.Store = FakeStore
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")
    dt.UTC = timezone.utc
    dt.utcnow = lambda: datetime.now(timezone.utc)
    dt.parse_datetime = lambda s: datetime.fromisoformat(s) if s else None
    util.dt = dt
    for name, module in {"homeassistant": ha, "homeassistant.core": core, "homeassistant.helpers": helpers,
                         "homeassistant.helpers.storage": storage, "homeassistant.util": util,
                         "homeassistant.util.dt": dt}.items():
        sys.modules.setdefault(name, module)


def test_seen_by_id_title_and_back():
    import asyncio
    _stub_homeassistant()
    seen_module = base.load("seen")
    seen = seen_module.SeenFilms(None)
    asyncio.run(seen.async_load())
    calls = []
    unsub = seen.async_add_listener(lambda: calls.append(1))
    seen.add(COWARD, "Coward")
    assert seen.is_seen(COWARD, "Coward") and not seen.is_seen(SUDDEN, "All of a Sudden")
    seen.add(None, "  all of a  SUDDEN ")                                 # typed by hand, no id yet
    assert seen.is_seen(SUDDEN, "All of a Sudden")
    seen.add(SUDDEN, "All of a Sudden")                                   # the id takes over from the title
    assert [k for k, _, _ in seen.items()].count(SUDDEN) == 1
    assert not any(k.startswith("title:") for k, _, _ in seen.items())
    assert FakeStore.saved["films"][COWARD]["title"] == "Coward"
    assert seen.remove(None, "coward") and not seen.is_seen(COWARD, "Coward")
    assert not seen.remove("nothing")
    assert len(calls) == 4
    unsub()
    seen.remove(SUDDEN)
    assert len(calls) == 4
    # Kept: a new list reads what the store saved.
    seen.add(PRIMETIME, "Primetime")
    again = seen_module.SeenFilms(None)
    asyncio.run(again.async_load())
    assert again.is_seen(PRIMETIME, "Primetime")
