# Picks the Pi's address when a command isn't given -PiAddress.
# If pi_address.txt exists in the project folder, its first line is used.
# That file is only on this PC (it isn't in git), because each network gives the Pi a different address.

if (-not $PiAddress) {
    $PiAddress = "the-coolest-raspberry-pi.local"
    $SavedAddress = Join-Path $PSScriptRoot "..\pi_address.txt"
    if (Test-Path $SavedAddress) {
        $Line = (Get-Content $SavedAddress -TotalCount 1).Trim()
        if ($Line) { $PiAddress = $Line }
    }
}
