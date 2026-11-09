# Runs servo_test.py on the Pi. This can move the arm!
# It uses the copy already on the Pi, so run .\deploy first if the script has changed.
#
#   .\test_servo                                  gentle claw test
#   .\test_servo -Joint base                      gentle test of another joint
#   .\test_servo -Joint claw -Angles 45,60,30     your own angles
#   .\test_servo -Joint claw -Delay 2             wait 2 seconds after each move
#   .\test_servo -PiAddress 10.0.0.171            use an IP address instead of the name
#   .\test_servo -Joint base -Pulses 1500,2400    calibration: exact pulse lengths (500-2500 microseconds)

param(
    [string]$Joint = "claw",
    [string]$Angles = "",
    [string]$Pulses = "",
    [string]$Delay = "1",
    [string]$PiAddress = "",
    [string]$PiUser = "groot_the_builder"
)

. (Join-Path $PSScriptRoot "pi_address.ps1")

# Only simple values are passed on to the Pi. The Pi script checks the joint limits.
if ($Joint -notin @("claw", "base", "shoulder", "elbow")) {
    Write-Host "Joint must be claw, base, shoulder or elbow. Nothing moved." -ForegroundColor Yellow
    exit 1
}
if ($Angles -and $Angles -notmatch '^\d+(,\d+)*$') {
    Write-Host "Angles must be whole numbers with commas and no spaces, like 45,60,30. Nothing moved." -ForegroundColor Yellow
    exit 1
}
if ($Pulses -and $Pulses -notmatch '^\d+(,\d+)*$') {
    Write-Host "Pulses must be whole numbers with commas and no spaces, like 1500,2400. Nothing moved." -ForegroundColor Yellow
    exit 1
}
if ($Delay -notmatch '^\d+(\.\d+)?$') {
    Write-Host "Delay must be a number of seconds, like 1 or 0.5. Nothing moved." -ForegroundColor Yellow
    exit 1
}

$Command = "cd ~/roboticArm && python3 -u servo_test.py --joint $Joint --delay $Delay"
if ($Angles) {
    $Command += " --angles $Angles"
}
if ($Pulses) {
    $Command += " --pulses $Pulses"
}

Write-Host "Testing $Joint on the Pi. Keep fingers clear. Press Ctrl+C to stop."
ssh -t -o ConnectTimeout=10 "$PiUser@$PiAddress" $Command
$Result = $LASTEXITCODE

if ($Result -eq 255) {
    Write-Host ""
    Write-Host "Couldn't connect to the Pi. Nothing moved." -ForegroundColor Yellow
    Write-Host "Check that it's on and on this network, or try: .\test_servo -PiAddress 10.0.0.171"
}
exit $Result
