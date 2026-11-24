# 🚌 BusTracker: Naryn buses on a map

Django project website suitable for mobile and computer screens.

## How to run

You need Python 3.10+ (on Windows, tick "Add Python to PATH" during installation).
Open a terminal in the `bustracker` folder (the one with `manage.py`):

```bash
python -m venv venv
venv\Scripts\activate             # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py load_demo        # demo routes, buses, users and marks
python manage.py runserver
```

Open http://127.0.0.1:8000 · Stop the server with `Ctrl+C`.
Next time you only need to activate `venv` and run `python manage.py runserver`.

| Role | Username / password | Can do |
|---|---|---|
| Guest | — | view the map, routes, buses and marks |
| User | `aibek` / `demo12345` (or sign up) | + create marks, edit and delete **their own** |
| Admin | `admin` / `admin12345` | + edit and delete any mark, create and edit routes on the map |

Tests: `python manage.py test transit`

## Structure

```
config/                   settings and root URLs
transit/
  models.py               Route, Stop, RouteStop, Bus, BusPosition, MarkCategory, Mark
  forms.py                SignUpForm, MarkForm, RouteForm
  views.py                pages + JSON API for the map
  services/
    geo.py                distance_m(), Polyline class
    location.py           LocationProvider (ABC) → MockProvider, DriverGPSProvider
    marks.py              MarkService: business rules for marks
    routes.py             RouteService: saves a route with its stops
  management/commands/load_demo.py
  templates/, static/
```

## Where the OOP is

| Principle | Where |
|---|---|
| Abstraction | `LocationProvider`: an abstract class with a `get_position()` method |
| Polymorphism | `MockProvider` and `DriverGPSProvider` implement `get_position()` differently; the API doesn't know which one is used (`services/__init__.py`) |
| Inheritance | `TimeStampedModel` → `Route`, `Stop`, `Bus`, `Mark`; the providers inherit from `LocationProvider` |
| Encapsulation | `Polyline` hides the length and point-on-line math; `MarkService` holds the rules; `Mark.can_edit()` |

## Business rules

1. Marks and route points must be inside the city bounds.
2. At most 10 marks per user per day.
3. A user can't place a mark of the same category within 20 m of one of their existing marks.
4. Only the author or an admin can edit or delete a mark.
5. A route line has at least 2 points.
6. If a bus's GPS position is older than 2 minutes, it is shown as offline (`DriverGPSProvider`).

## How a route is drawn

An admin opens "+ Route". In "Line" mode they click along the streets in the order the bus
drives. In "Stops" mode they click where a stop is and type its name. The line is stored in
`Route.path` (JSON `[[lat, lng], ...]`), and the stops in `Stop` + `RouteStop` (with order).
Mock buses drive back and forth along that line.

## Real GPS (future work)

In `transit/services/__init__.py`, replace `MockProvider()` with `DriverGPSProvider()` and add
a driver page that sends points to `BusPosition` using `navigator.geolocation.watchPosition`.
This only works over HTTPS.

The demo route coordinates are approximate.
