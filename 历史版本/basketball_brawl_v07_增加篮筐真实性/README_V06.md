# Version 0.6 - Charge Shot System

## New shooting controls

- Player 1: hold `Space` to charge, release to shoot.
- Player 2: hold `Enter` to charge, release to shoot.
- The green section of the meter is the perfect-release window.
- Releasing too early makes the ball fall short.
- Releasing too late sends the ball long.
- Holding until the meter is full automatically releases the shot.

## Character shooting differences

- DJH: widest perfect window and the most stable shot.
- Gorilla: slow charge and narrow perfect window.
- Ninja: faster charge with a medium perfect window.

AI shooting continues to work automatically and still uses the selected difficulty.

## Files changed

- `constants.py`
- `characters.py`
- `entities.py`

The arena and character ability systems from Version 0.5 are retained.
