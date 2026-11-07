"""Named moves. To add one, add a name and its list of (joint, angle) steps."""

MOVES = {
    "claw_wiggle": [
        ("claw", 45),
        ("claw", 60),
        ("claw", 45),
        ("claw", 30),
        ("claw", 45),
    ],
    "wave": [
        ("base", 70),
        ("base", 110),
        ("base", 90),
    ],
}
