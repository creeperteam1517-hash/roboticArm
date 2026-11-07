# Makes a new secret code on the Pi for claude.ai Jarvis, and shows it once.
# Run .\deploy first, so remote_token.py is on the Pi.
#
#   .\remote_token
#   .\remote_token -PiAddress 10.0.0.171

param(
    [string]$PiAddress = "the-coolest-raspberry-pi.local",
    [string]$PiUser = "groot_the_builder"
)

ssh -t -o ConnectTimeout=10 "$PiUser@$PiAddress" "cd ~/roboticArm && python3 remote_token.py"
if ($LASTEXITCODE -eq 255) {
    Write-Host "Couldn't connect to the Pi. Try: .\remote_token -PiAddress 10.0.0.171" -ForegroundColor Yellow
}
exit $LASTEXITCODE
