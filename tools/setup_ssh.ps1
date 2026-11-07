# One-time setup: lets this PC log in to the Pi without typing a password.
# Safe to run again. It will not replace a key you already have.

param(
    [string]$PiAddress = "the-coolest-raspberry-pi.local",
    [string]$PiUser = "groot_the_builder"
)

$Target = "$PiUser@$PiAddress"
$SshDir = Join-Path $HOME ".ssh"
$KeyPath = Join-Path $SshDir "id_ed25519"
$HostKeyOption = "StrictHostKeyChecking=accept-new"

function Test-KeyLogin {
    ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o $HostKeyOption $Target "exit" 2>$null
    return ($LASTEXITCODE -eq 0)
}

# Step 1: make a key on this PC, if there isn't one yet.
if (Test-Path $KeyPath) {
    Write-Host "Step 1 of 3: This PC already has a key. Keeping it."
} else {
    Write-Host "Step 1 of 3: Making a key for this PC..."
    New-Item -ItemType Directory -Force $SshDir | Out-Null
    ssh-keygen -q -t ed25519 -f $KeyPath -N '""' -C "roboticArm-deploy"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Couldn't make the key. Nothing on the Pi has changed." -ForegroundColor Yellow
        exit 1
    }
}

# Step 2: give the Pi this PC's public key, unless it already works.
if (Test-KeyLogin) {
    Write-Host "Step 2 of 3: The Pi already knows this PC. Skipping."
} else {
    Write-Host "Step 2 of 3: Sending the key to the Pi."
    Write-Host "Type the Pi's password when asked. The letters won't show as you type. That's normal."
    Get-Content "$KeyPath.pub" | ssh -o ConnectTimeout=10 -o $HostKeyOption $Target "mkdir -p ~/.ssh && chmod 700 ~/.ssh && tr -d '\r' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Couldn't reach the Pi at $PiAddress. Nothing is broken." -ForegroundColor Yellow
        Write-Host "Check that the Pi is on, and on the same network as this PC, then run this again."
        Write-Host "If you know the Pi's IP address, you can use it instead:"
        Write-Host "  .\setup_ssh -PiAddress 192.168.1.50   (use your Pi's real address)"
        exit 1
    }
}

# Step 3: prove it works.
Write-Host "Step 3 of 3: Checking the login..."
if (Test-KeyLogin) {
    Write-Host "All set! This PC can now log in to the Pi without a password." -ForegroundColor Green
} else {
    Write-Host "The key was sent, but the login check didn't pass. Nothing is broken, just share this message with Claude." -ForegroundColor Yellow
    exit 1
}
