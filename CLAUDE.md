# Robotic arm project

Read `brain.md` first. It has the hardware, wiring, current status and next steps.

## Working with me
- I'm a beginner with electronics. Go one small step at a time, in plain English, with exact commands.
- I can get scared and frustrated easily, so be kind and reassuring.
- Write files for me instead of giving me long code to type.

## Safety
- Only run a command that can move the arm when I ask for that movement. That means `.\arm <move>`, `.\test_servo` and `.\deploy -Run`.
- Before running new code, run `.\deploy` and confirm it worked. Wait for that result before starting anything that can move the arm, because an old copy on the Pi can ignore new options and still move.
- A script finishing without errors doesn't prove the arm moved. Ask me what I saw.
- Don't raise the joint limits in `pi/arm.py` unless we've measured the real limits.
- I type passwords myself, in the terminal. Never enter one for me. Never write one in a file.

## Git
- When I ask for a commit, commit on `main` and push in the same step.
- Leave `.claude/` out of commits.

## Running commands
- The scripts are Windows only. Run them from the project folder.
- For commands that may need my password or Ctrl+C, use my Terminal panel so I can type.

## Keep this up to date
Update `brain.md` when something real changes, so another computer can pick up from there.
