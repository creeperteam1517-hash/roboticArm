# Opens a prompt on the Pi where you type Jarvis's keys. The keys stay on the Pi.
# Run .\deploy first, so set_keys.py is on the Pi.
#
#   .\set_keys
#   .\set_keys -PiAddress 10.0.0.171

param(
    [string]$PiAddress = "the-coolest-raspberry-pi.local",
    [string]$PiUser = "groot_the_builder"
)

ssh -t -o ConnectTimeout=10 "$PiUser@$PiAddress" "python3 ~/roboticArm/set_keys.py"
if ($LASTEXITCODE -eq 255) {
    Write-Host "Couldn't connect to the Pi. Try: .\set_keys -PiAddress 10.0.0.171" -ForegroundColor Yellow
}
exit $LASTEXITCODE
