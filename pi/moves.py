"""Named moves. To add one, add a name and its list of (joint, angle) steps."""

MOVES = {
    "claw_wiggle": [
        ("claw", 45),
        ("claw", 60),
        ("claw", 45),
        ("claw", 30),
        ("claw", 45),
    ],
    "clap": [
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 45),
    ],
    "wave": [
        ("base", 70),
        ("base", 110),
        ("base", 90),
    ],
    "base_sweep": [
        ("base", 0),
        ("base", 180),
        ("base", 0),
        ("base", 180),
    ],
    "victory_dance": [
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 10), ("claw", 80),
        ("claw", 45),
        ("base", 60),
        ("base", 120),
        ("base", 90),
    ],
}

# Seconds to wait after each step, for moves that don't use the normal 1 second.
DELAYS = {
    "clap": 0.5,
    "victory_dance": 0.5,
}
