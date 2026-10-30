# Cineville for Home Assistant

What plays in the Cineville theaters of a city, and what comes soon, as two sensors. Made for the Tessera plugin
`cineville` (`plugins/cineville` in [woldhek/tessera-plugins](https://github.com/woldhek/tessera-plugins)), and useful on its own in a dashboard or an automation.

It reads api.cineville.nl, the public service the Cineville website itself reads: no account and no key.

## Install

1. In HACS, open the menu at the top right, choose **Custom repositories**, and add
   `https://github.com/woldhek/ha-cineville` with the type **Integration**.
2. Find **Cineville** in HACS, download it, and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Cineville**: choose a city, then (if you like) only some of its
   theaters, how many days ahead, the order, how far "Coming soon" looks ahead, and the language of the descriptions.
   Set up another city, or another choice of theaters, by adding the integration again.

## The sensors

Each city makes a device with two sensors; the state of each is its number of films.

- **Now showing** (`sensor.cineville_<city>_now_showing`): the films with a showtime in the chosen theaters and days.
- **Coming soon** (`sensor.cineville_<city>_coming_soon`): the films that open in the Netherlands in the coming weeks,
  soonest first, with how many previews the chosen theaters have.

Their attributes:

| Attribute | What |
|---|---|
| `films` | Up to 60 films: `title`, `directors`, `year`, `duration`, `premiere`, `highlight` (`week`, `tip` or empty), `tip_by`, `shows`, `shows_today`, `next_start`, `next_venue`, `venues`, `preview`, `classic`, `description`, `poster`, `url` |
| `titles`, `highlights`, `directors`, `shows` | The first 16 films as short lists, for a Tessera screen |
| `shows_today`, `next_start` (seconds since 1970), `next_venue` | The same, for "Now showing" |
| `premieres` (noon of the day it opens, seconds since 1970) | The same, for "Coming soon" |
| `cineville_list` | `now` or `soon` |
| `city`, `venues` | The city and the theaters it counts |

## Films you have seen

Each city also has a to-do list, **Seen**, with the films you have seen; every city's list shows the same films. Mark a
film seen with the action `cineville.mark_seen`, from the Tessera screen, or by adding its title to the list. With the
option **Hide films I have seen** (on by default) a film on the list leaves Now showing and Coming soon at once; delete
it from the list, or untick it, to see it again. The list is kept in Home Assistant's storage, by Cineville's own id
of each film.

## Trailers and the blurb

- `films` gives each film its `description` (a short blurb) and its `trailer` (an MP4 at Cineville).
- **Media → Cineville** in Home Assistant lists the trailers, to play on any media player that plays video.
- The action `cineville.play_trailer` plays a film's trailer on a media player: the one you name, or the one of the
  option **Media player for trailers**.
- The action `cineville.get_film` answers everything about one film: its blurb (whole, and as `blurb_lines` for a
  Tessera screen, which cuts every text to 48 bytes), director, year, duration, the next showtimes with their theater,
  whether it has a trailer and you have seen it.

```yaml
action: cineville.get_film
data:
  film: All of a Sudden     # a title, or Cineville's id of the film
response_variable: film
```

"Recommended first" puts Cineville's own picks on top: the film of the week, then the tips of its editors, then what
shows most. The lists are kept out of the recorder's history. It asks Cineville once an hour.

## Tests

`python3 -m pytest tests` runs the client and the lists against answers of the API, without Home Assistant.
