# Copies install_tailscale.sh to the Pi and runs it, so you can type the Pi's password.
#
#   .\install_tailscale
#   .\install_tailscale -PiAddress 10.0.0.171

param(
    [string]$PiAddress = "",
    [string]$PiUser = "groot_the_builder"
)

. (Join-Path $PSScriptRoot "pi_address.ps1")

$Target = "$PiUser@$PiAddress"
scp -q -o ConnectTimeout=10 (Join-Path $PSScriptRoot "install_tailscale.sh") "${Target}:/tmp/install_tailscale.sh"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Couldn't reach the Pi. Try: .\install_tailscale -PiAddress 10.0.0.171" -ForegroundColor Yellow
    exit 1
}
ssh -t $Target "tr -d '\r' < /tmp/install_tailscale.sh > /tmp/install_tailscale_lf.sh && bash /tmp/install_tailscale_lf.sh"
exit $LASTEXITCODE
