# PROJECT HANDOFF: Vision-guided robot arm with Jarvis as the front end

## ME
- Hobbyist, beginner with electronics. Please go ONE small step at a time, plain English, exact commands, no long code for me to type (write files for me instead). I get scared and frustrated easily, so reassure me kindly. I like real photos or clear images over diagrams.

## GOAL
- Build a 3D-printed EEZYbotARM Mk2 (printed on a Bambu P2S) that does vision-guided pick-and-place.
- "Jarvis" is the front end (a chat/console page I built earlier with Claude): https://claude.ai/artifact/2xNeQuiwphvp232UuiJmPW
- Jarvis sends commands to code running on the Raspberry Pi, and the Pi moves the arm.

## HARDWARE
- Raspberry Pi 5, Raspberry Pi OS 64-bit
  - Hostname: the-coolest-raspberry-pi
  - Username: groot_the_builder (lowercase)
  - SSH is enabled. I2C is enabled.
- PCA9685 16-channel servo driver (blue board)
- 4 servos on the arm:
  - claw (SG90) on channel 0
  - base on channel 1
  - shoulder on channel 2
  - elbow on channel 3
- Old joint limits (degrees): base 10-170, claw 10-80, shoulder 60-120, elbow 50-130
- Servo power: 6V DC wall supply (black, green screw-terminal plug, no +/- marks)
  - Path: supply + -> 5A fuse in an inline holder -> PCA9685 V+ (right screw)
  - Supply - -> PCA9685 GND (left screw)
- The Arduino Uno is dead (reversed polarity), so we switched to the Pi + PCA9685.
- Planned: Pi Camera Module 3 or a USB webcam for vision.
- Budget: about $200 or more.

## WIRING (Pi to PCA9685)
- Pin 1 (3.3V) -> VCC
- Pin 3 (SDA) -> SDA
- Pin 5 (SCL) -> SCL
- Pin 6 (GND) -> GND
- OE and V+ on the logic side are left empty. Don't use 5V pins 2/4.
- Verified: `sudo i2cdetect -y 1` shows 40 (PCA9685) and 70 (all-call).

## STATUS
- Done: I2C wiring verified. 6V supply, fuse and holder wired to the PCA9685 power block.
- **Power polarity not measured yet.** The claw moving is a good sign that it's right, but I chose to skip the meter check, so there's still no reading. Please have me measure DC volts at the PCA9685 V+ (right) and GND (left) with the servo UNPLUGGED. Black probe on GND, red on V+. It should read about +6 (a minus sign means reversed). A fuse does not protect against reversed polarity.
- Multimeter: KAIWEETS KM100, dial on 20 in the DC V section, black probe in COM, red probe in VOmA.
- Done: SSH key login works from my PC. pi/servo_test.py is on the Pi in ~/roboticArm. python3-smbus2 is installed.
- Done on 2026-11-06: the claw (channel 0) moved in the gentle test. An earlier run that same night finished without errors but the claw didn't move, and the cause is unknown. If it happens again, check the 6V power first.
- The claw moved from 10 to 80 with no strain on 2026-11-06, so the claw limits look okay for now.
- The base (channel 1) moved from 10 to 170 with no strain on 2026-11-06, so the base limits look okay for now.
- **The base sometimes doesn't move, even though the script finishes without errors.** It happened in `.\arm wave`, and again in the base sweep right after five claw claps (right after a Pi restart). The base-only sweep moved straight after that. Cause unknown. Next: with the 6V supply unplugged, check the base servo's plug and wires for a loose connection. Then check the power, because the 6V supply is still unmeasured.
- 2026-11-09: the base (0 and 90) and claw_wiggle all finished without errors but nothing moved. The Pi saw the PCA9685 fine (it answered at 0x40) and wasn't short on power. The cause: **the fuse holder had no fuse in it**, so the servos had no 6V power. With the power fixed, the base moved to 0. If nothing moves but the scripts say "done", check the fuse first.
- On 2026-11-07 the base once stopped short of 170 during `-Angles 10,170 -Delay 10`, cause unknown. Later, moving to 10 and then to 170 as two separate commands with a 1-second wait reached 170. Commands can't send 180, because the limit is 170.
- 2026-11-08 base calibration (exact pulses with `.\test_servo -Joint base -Pulses ...`, me watching): moved freely at 2300, 2400 and 2500 microseconds (the top of the safe range), hit its hard stop at 600, and rested quietly at 650. pi/arm.py now maps base 0..180 degrees to 650..2500 microseconds (PULSE_RANGE), and the base limits are 0 to 180. base_sweep now uses 0 and 180. The old 600..2400 mapping only used part of the base's travel, which is why 10 to 170 looked like much less than 160 degrees. The claw, shoulder and elbow still use 600..2400 and aren't calibrated. The claude.ai Jarvis Robot tab is updated to base 0..180 too (version 43, which also keeps the speaking speed and pitch settings added in version 42). Confirmed: base_sweep (0, 180, 0, 180) gave a full swing with no strain.
- Older note: the base's lowest limit in pi/arm.py was 8, confirmed with no strain on 2026-11-07. A move to 6 ran, but I didn't report how it looked. A try at 0 showed no movement, so 0 is unconfirmed. I remember reaching 0 before.
- On 2026-11-07 the Pi stopped answering on the network, and restarting it fixed that. Cause unknown. The Pi's .local name also only works some of the time, so use `-PiAddress 10.0.0.171` if it fails.
- Not done: shoulder and elbow haven't been tested.
- Old servos may have been stressed by the earlier reverse-polarity incident, so test each one.

## CURRENT BLOCKER
- No blockers right now. Worth measuring power polarity (see STATUS) before connecting the other servos.
- To do soon: change the Pi password with `passwd`, because it was accidentally pasted into a Claude chat.

## DEPLOYING TO THE PI
- Code for the Pi lives in the `pi/` folder. It gets copied to `~/roboticArm` on the Pi.
- Run these from the project folder in a terminal on my PC.
- First time only: `.\setup_ssh` (asks for the Pi password once).
- Every time: `.\deploy` copies the files, installs missing packages and restarts the Jarvis page. It doesn't move the arm.
- To also run a script: `.\deploy -Run servo_test.py`. This can move the arm. Check polarity first.
- If the name doesn't work, add `-PiAddress <the Pi's IP>` to either command.
- Tested on the real Pi on 2026-11-06, at 10.0.0.171 on my home Wi-Fi. That address could change. If so, get the new one with `hostname -I` on the Pi.
- The `.cmd` files are launchers, so the scripts in `tools/` run without changing the Windows script security setting.
- Possible later addition: Tailscale, to reach the Pi from any location.

## USING ANOTHER COMPUTER (Windows)
1. Install Git and Claude Code. Windows already includes SSH.
2. Run `git clone https://github.com/creeperteam1517-hash/roboticArm.git`, then `cd roboticArm`.
3. Run `.\setup_ssh` once on that computer. I type the Pi's password in the terminal.
4. Run `.\arm` to list the moves. This doesn't move the arm, and it proves the login works.
- The computer and the Pi must be on the same network, unless Tailscale is set up.
- The scripts don't run on Mac or Linux. Claude would need to write versions for that system.
- 2026-11-09: set up a second Windows PC. It's on the "Livin" Wi-Fi (addresses start with 192.168.50.), and the Pi's name didn't work there. On the Pi's own screen and keyboard, I joined the Pi to Livin with `sudo nmcli dev wifi connect "Livin" password "<password>"`. It got 192.168.50.78. Then `.\setup_ssh -PiAddress 192.168.50.78` worked, and `.\arm -PiAddress 192.168.50.78` listed the moves. The Pi still remembers the home Wi-Fi (10.0.0.171) and SigmaNetwork_Upstairs.
- The same day, claude.ai Jarvis's Check failed with an SSL "UNEXPECTED_EOF" error from the Funnel address. That means Tailscale's relay couldn't reach the Pi (the Pi was offline from Tailscale), not a Jarvis bug. After the Pi joined Livin, Tailscale and Funnel were back: the remote entrance answered 401 without a code, as it should. `.\deploy` worked, and the Jarvis page is at http://192.168.50.78:8000.
- Saved address: if the Pi's name doesn't work on a network, put its address on the first line of `pi_address.txt` in the project folder. Every command (`.\arm`, `.\deploy`, `.\test_servo`, `.\set_keys` and the rest) then uses it, so `-PiAddress` isn't needed. The file stays on that PC only (it's in .gitignore). `-PiAddress` still overrides it. This PC's file says 192.168.50.78. If the Pi's address changes, run `hostname -I` on the Pi and update the file.

## MOVING THE PI TO A NEW LOCATION
- The Pi only joins Wi-Fi it already knows, and I may not have a screen there. Before leaving, add the new Wi-Fi details, or a phone hotspot as a backup.
- The address 10.0.0.171 only applies to my home network. Try the Pi's name first. If that fails, find the Pi in the router's or hotspot's device list, then add `-PiAddress <address>` to commands.
- Optional: install Tailscale before leaving, to reach the Pi from anywhere while it's online.

## SERVO TEST
pi/servo_test.py moves one joint through a list of angles, then releases it. It refuses angles outside the old joint limits before anything moves. The real limits still need measuring.

Run from my PC, without copying files first. This can move the arm:

```
.\test_servo
.\test_servo -Joint base
.\test_servo -Joint claw -Angles 45,60,30 -Delay 2
```

Add `-PiAddress 10.0.0.171` if the name doesn't work. If the script has changed, run `.\deploy` first.

## JARVIS CHAT PAGE
- Open http://10.0.0.171:8000 in a browser on the same network. No monitor is needed on the Pi. The `the-coolest-raspberry-pi.local` name also works at port 8000 when the name is working.
- It has routine buttons, claw and base sliders, a chat, and a big Stop button, merged on one page as I asked. The buttons, sliders and Stop work with no keys. The chat answers questions and moves the arm when asked, and switches on once the Claude key is set. Replies are read aloud in George's voice (ElevenLabs), or the browser's own voice if there's no ElevenLabs key.
- Shoulder and elbow sliders stay locked until unlocked on the page. A slider position holds for 10 seconds, then relaxes.
- Chat uses Claude (`claude-opus-5-5`, low effort, with automatic fallback if Claude declines) through the official anthropic library, 1.x, in its own environment on the Pi at ~/.local/share/jarvis/venv. `.\deploy` installs it.
- Keys: run `.\set_keys` on the PC and type the Claude key (and optionally the ElevenLabs key) in the terminal. They're saved only on the Pi, in ~/.config/jarvis/keys.env, readable only by my user, never in this repo. The Claude API is paid separately from a Claude subscription.
- Chat can run routines, move the claw or base to an angle, stop, and check status. It can't move the shoulder or elbow until they're tested. It only moves the arm when my latest message asks. It can't see the arm, so it says commands were sent, not that the arm moved.
- One shared conversation for everyone using the page. "New chat" clears it, and it starts fresh by itself after 30 messages.
- 2026-11-09: the chat is saved on the Pi in ~/.local/share/jarvis/chat.json, so refreshing the page or restarting Jarvis keeps it. The page shows it again on load, and Claude gets it back as plain text turns. I confirmed it stays after a refresh. Jarvis also now always says "sir" (it used to ask "sir or ma'am").
- 2026-11-08, "independent Jarvis" stage 1 and 2 (deployed, tested with fakes only): the Pi chat now has the claude.ai Jarvis's personality (British butler, humour, warmth), live web search (Claude's web_search_20260209 server tool, max 3 per answer), memory, tasks and reminders. These are saved on the Pi in ~/.local/share/jarvis/data.json (pi/jarvis_data.py), and the page has a Tasks and Reminders panel. Reminders are spoken while the page is open. George's voice on the Pi uses eleven_flash_v2_5. There's a microphone button, which only works on a secure address.
- To switch it all on: (1) run `.\set_keys` and enter a paid Claude API key (and my free ElevenLabs key for George); (2) for the microphone and use away from home, run `ssh -t groot_the_builder@10.0.0.171 "sudo tailscale serve --bg --https=8443 8000"` and open https://the-coolest-raspberry-pi.taile11589.ts.net:8443 on a device signed in to the Tailscale app. That address is private to my Tailscale devices. Funnel on port 443 stays only for the locked remote entrance.
- Not built yet (stage 3): files, 3D workshop, Tripo.
- The Pi chat model is claude-sonnet-5-5 (my choice, about half the cost of Opus). Rough cost estimate with $5 of credit: about 400–500 chat messages, fewer with web searches.
- 2026-11-08: the Pi page now uses the claude.ai "Jarvis Assistant" look, as I asked: orb, clock, side tabs (Tasks, Robot with routines, sliders and Stop, Alerts for reminders), and the chat console with New chat, voice, microphone and an always-visible Stop arm button. On a phone the tabs open with the Panel button. Files, 3D and Tripo tabs are left out until they're built on the Pi.
- 2026-11-08: Claude API and ElevenLabs keys are added on the Pi (with set_keys). A test chat replied in about 9 seconds without moving the arm, and George's voice clip worked on the Pi.
- 2026-11-09, on Livin at http://192.168.50.78:8000: the page loaded ("Online via Claude", no errors). I tried the chat and a robot button, and both worked.
- The Clap button moved the real claw on 2026-11-07, before the chat was added. The merged page was tested with a fake board and a fake Claude, but hasn't run with real keys, and chat hasn't moved the real arm yet.
- Files: pi/jarvis_server.py, pi/jarvis_chat.py, pi/jarvis.html, pi/jarvis.service, pi/set_keys.py. It runs as a user service on the Pi, so `.\deploy` copies and restarts it without a password. It's set to start when the Pi turns on, but that hasn't been tested with a restart yet.
- It has no password, so anyone on the Wi-Fi can use the buttons, chat with it, move the arm, and spend Claude credit. Keep it off the public internet. It refuses commands sent from other websites.
- The older Jarvis on claude.ai still has its own features (tasks, files, 3D, Tripo), but its arm controls only worked with the old Arduino over USB.

## REMOTE ARM CONTROL (claude.ai Jarvis -> Composio -> Pi)
- Goal: let the claude.ai Jarvis move the arm using my Claude subscription, with no API key.
- How it works: claude.ai Jarvis runs a small request in Composio's cloud workbench, which sends it to the Pi's public Tailscale Funnel address https://the-coolest-raspberry-pi.taile11589.ts.net. Funnel passes it to a locked "remote entrance" inside the Pi (127.0.0.1:8001, in pi/jarvis_server.py).
- The remote entrance only offers: arm state, run a routine, move the claw or base, and stop. Every request needs the secret code in the X-Jarvis-Token header. Wrong codes are refused and slowed down. The home page, chat, voice and keys aren't reachable from the internet.
- Secret code: make it with `.\remote_token` (shown once, saved only on the Pi). Making a new one locks out the old one. It goes into the Robot tab of claude.ai Jarvis, saved per device. Never paste it into a Claude chat.
- Tailscale 1.104.5 is installed on the Pi (`.\install_tailscale`), signed in to my account. Funnel was turned on 2026-11-07 for port 8001.
- To turn public access off: `ssh -t groot_the_builder@10.0.0.171 "sudo tailscale funnel --https=443 off"`
- Tested 2026-11-07: from the internet, no code and a wrong code got 401, and the home page and chat were refused. Composio's workbench reached the entrance (with a wrong code, so nothing moved).
- The claude.ai Jarvis (https://claude.ai/artifact/2xNeQuiwphvp232UuiJmPW, version 22, 2026-11-07) now has a Robot tab that talks to the Pi: routines, claw and base controls, Stop, and a box to save the secret code on each device. Its robot tool for chat uses the same routes. It hasn't been tried with the real code yet.
- Jarvis voice tweaks (versions 23 to 27, 2026-11-07): George speaks about 15% faster (the Speed slider applies to him, pitch unchanged). Arm commands are sent in the background so Jarvis replies right away, and failures still show in chat. He says "Very well, sir" or "As you wish, sir" the moment an arm command goes out, from audio saved on each device. Short phrases are saved per device, so they play instantly. Composio's managed ElevenLabs only allows the multilingual_v2 model at mp3_44100_128, so the faster flash model isn't available. I said the remaining wait (Claude thinking) is good enough.
- Version 28: "pose" moves the claw and base in one command, and "move the claw and base" with no angles runs victory_dance. Version 29: one random acknowledgement per arm command from 14 original butler-style phrases (never the same twice in a row), spoken by the page. Claude is told not to add its own, and any it adds are skipped. Confirmed it says just one.
- Version 30 (2026-11-07): Composio removed its search toolkit (COMPOSIO_SEARCH_*) from this account ("not available in Composio For You"), which broke Jarvis's web, news and page-reading lookups. They now run in Composio's workbench, using its built-in web_search helper and requests with BeautifulSoup. Weather (WEATHERMAP_WEATHER) still works directly. Search answers no longer come with source links.
- Version 31: a microphone button next to + uses the browser's speech recognition (in Chrome this sends audio to Google to transcribe) and sends what I said to Jarvis. claude.ai's list of page permissions doesn't include the microphone, so it may be blocked there. If it is, Jarvis explains the fallback: Windows key + H dictation on a PC, or the keyboard microphone on a phone. Tried on claude.ai: the microphone is blocked. Version 32: once blocked, the button becomes a dictation helper. It focuses the message box and shows the Windows key + H (or phone keyboard) hint, with no error each time.
- Version 33: more emotion and humour in Jarvis's personality. Version 34: George is the only voice (the device voice and Roger/Daniel are removed), at natural speed. One shared audio player is unlocked on the first tap, because phones blocked sound that started after a delay. A failed audio chunk retries once, then shows a note instead of switching voices. On phones the AI effect is off (it needs the computer's audio engine). Version 34's shared audio player didn't work at all on my phone. Version 35 went back to the original playback through the page's audio engine (with the AI effect everywhere again). Each tap wakes that engine, and each reply wakes it before speaking. George only, the retry, and the failure note are kept.
- 2026-11-08: George went silent because my Composio wallet ran out of credits ("Metering_WalletBalanceExhausted", status 402). Composio charges about $0.0036 per managed ElevenLabs clip. Making the 14 phrases ahead of time, the retries, and Claude's own test clips used credit up faster. Version 36: no phrases made ahead of time, no retry when out of credit, and a friendly note telling me to add credit in the Composio dashboard or connect my own free ElevenLabs account to Composio. Arm commands and web search also go through Composio's workbench, so they may stop if credit runs out too.
- Version 37: by my choice, the default voice is now the free built-in voice of the phone or computer (Jarvis prefers a British male voice, such as Daniel on an iPhone). It's instant and costs nothing. George (ElevenLabs via Composio) is still an option under Voice ▾, but costs credit. The first tap unlocks speech on iPhones. I found the built-in voice awful.
- Version 38: I picked a new ElevenLabs voice, "George" (upbeat English male with a neutral accent, Voice Library ID WrjxnKxK0m1uiaH0uteU, https://elevenlabs.io/voices/WrjxnKxK0m1uiaH0uteU). It's the default again, and the built-in voice is the other option. It won't speak until Composio has credit or my own ElevenLabs account is connected in Composio. Library voices may also need adding to my own ElevenLabs account. Not heard yet.
- Version 39: I asked Claude to pick the free option, so the plan is to connect my own free ElevenLabs account to Composio. Jarvis is back on the original standard George (JBFqnCBsd6RMkjVDRZzb), which free accounts can use. The upbeat Library George may need a paid ElevenLabs plan to use through Composio. Next: make the ElevenLabs account and connect ElevenLabs in the Composio dashboard with my own API key.
- 2026-11-08: my own free ElevenLabs account is connected in Composio (alias "jarvis", free tier, 10,000 characters a month). The API key has only Text to Speech, Voices (read), Models and User access. Through my own account Composio charges nothing, and the faster eleven_flash_v2_5 engine is allowed. Version 40 uses Flash at mp3_22050_32 (half the allowance per character, small files, no ffmpeg). If the monthly allowance runs out, Jarvis shows a note, and the built-in voice is the free fallback under Voice ▾. Confirmed: George talks on my iPhone (Claude app) with version 40.
- Tailscale also lets my Tailscale devices reach the Pi from other locations.

## NAMED MOVES
- pi/arm.py is the shared code that moves joints and enforces the limits. Every script should use it.
- pi/moves.py holds the named moves. To add one, add a name and its (joint, angle) steps, then run `.\deploy`.
- `.\arm` lists the moves. `.\arm claw_wiggle` runs one and can move the arm. `-Delay 2` waits longer after each step.
- `.\arm claw_wiggle` moved the real claw on 2026-11-06.
- Moves so far are `claw_wiggle`, `clap` (claw 10 to 80, five times), `wave` and `base_sweep` (base), and `victory_dance` (three claps, then a base swing).
- 2026-11-09: added 15 more claw and base moves: nod, shake_head, look_left, look_right, scan, pendulum, sleepy, snap, chomp, drum_roll, grab, release, high_five, spin_and_snap and party. All angles are inside the limits, but none have run on the real arm yet. To add a move, change pi/moves.py and run `.\deploy`. Its button appears on the Jarvis page, and chat can use it straight away. Shoulder and elbow haven't been tested, so they have no moves yet. There's no smooth motion yet.
- claude.ai Jarvis version 44 (2026-11-09): the Robot tab and its chat tool have all 20 routines. Jarvis always says "sir" there too (it no longer switches to "ma'am" based on memory). The Pi already accepts the new routines through the remote entrance.
- 2026-11-09: Pi Jarvis chat now holds arm moves until the reply starts playing (the page calls /api/chat/go when the voice starts). The moves start anyway after 6 seconds if the page never calls, and straight away if the voice is off. Stop cancels a held move. Tried on the real arm, and it speaks as the arm moves.
- Possible later addition: a Claude skill that runs these moves, only when I ask for it directly.

The claw servo goes on channel 0: orange/yellow wire on the yellow pin, red in the middle, brown/black on the black pin. 6V supply on.

## NEXT STEPS
1. Confirm polarity with the meter.
2. Test the other servos one at a time (base ch1, shoulder ch2, elbow ch3) with `.\test_servo -Joint base` and so on. Measure the real joint limits.
3. Add smooth motion and moves for all four joints to pi/arm.py and pi/moves.py (limits are done). The old Arduino protocol was B/C/E/H<angle> (base/claw/elbow/shoulder), V<ms per degree>, S (stop), X (release).
4. Enter keys with `.\set_keys`, then try Jarvis chat on the real arm once the servo power is fixed.
5. Add the camera and vision-guided pick-and-place.
6. Later: redesign the printed plinth for the new hardware.
