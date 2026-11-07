# Runs a named move on the Pi. This can move the arm!
# It uses the code already on the Pi, so run .\deploy first if you've changed a move.
#
#   .\arm                              list the moves (the arm stays still)
#   .\arm claw_wiggle                  run a move
#   .\arm claw_wiggle -Delay 2         wait 2 seconds after each step
#   .\arm claw_wiggle -PiAddress 10.0.0.171    use an IP address instead of the name

param(
    [string]$Move = "list",
    [string]$Delay = "",
    [string]$PiAddress = "the-coolest-raspberry-pi.local",
    [string]$PiUser = "groot_the_builder"
)

# Only simple values are passed on to the Pi. The Pi checks the move and its limits.
if ($Move -notmatch '^[A-Za-z0-9_]+$') {
    Write-Host "Move names can only use letters, numbers and underscores. Nothing moved." -ForegroundColor Yellow
    exit 1
}
if ($Delay -and $Delay -notmatch '^\d+(\.\d+)?$') {
    Write-Host "Delay must be a number of seconds, like 1 or 0.5. Nothing moved." -ForegroundColor Yellow
    exit 1
}

if ($Move -ne "list") {
    Write-Host "Asking the Pi to run $Move. Keep fingers clear. Press Ctrl+C to stop."
}
$Command = "cd ~/roboticArm && python3 -u run_move.py $Move"
if ($Delay) {
    $Command += " --delay $Delay"
}
ssh -t -o ConnectTimeout=10 "$PiUser@$PiAddress" $Command
$Result = $LASTEXITCODE

if ($Result -eq 255) {
    Write-Host ""
    Write-Host "Couldn't connect to the Pi. Nothing moved." -ForegroundColor Yellow
    Write-Host "Check that it's on and on this network, or try adding: -PiAddress 10.0.0.171"
}
exit $Result
