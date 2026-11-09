# Copies everything in the pi folder to the Pi, in ~/roboticArm.
# It only runs code on the Pi if you ask with -Run, so a normal deploy never moves the arm.
# Files you delete from the pi folder are not deleted from the Pi.
#
#   .\deploy                        copy the files
#   .\deploy -Run servo_test.py     copy the files, then run that script on the Pi
#   .\deploy -PiAddress 192.168.1.50   use an IP address instead of the name

param(
    [string]$Run = "",
    [string]$PiAddress = "",
    [string]$PiUser = "groot_the_builder"
)

. (Join-Path $PSScriptRoot "pi_address.ps1")

# Pi OS packages the code needs. Add new ones to this list.
$Packages = @("python3-smbus2")

$Target = "$PiUser@$PiAddress"
$RemoteDir = "roboticArm"
$LocalDir = Join-Path (Split-Path $PSScriptRoot -Parent) "pi"
$HostKeyOption = "StrictHostKeyChecking=accept-new"

# Catch a mistyped script name before doing anything.
if ($Run -and -not (Test-Path (Join-Path $LocalDir $Run) -PathType Leaf)) {
    Write-Host "There's no file called '$Run' in the pi folder. Nothing was copied." -ForegroundColor Yellow
    exit 1
}

# Step 1: make sure the Pi can be reached.
Write-Host "Step 1 of 4: Looking for the Pi at $PiAddress..."
ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o $HostKeyOption $Target "mkdir -p ~/$RemoteDir" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Couldn't log in to the Pi. Nothing is broken, and nothing was copied." -ForegroundColor Yellow
    Write-Host "  - Check that the Pi is on, and on the same network as this PC."
    Write-Host "  - If this is your first time, run .\setup_ssh once."
    Write-Host "  - If the name doesn't work, try the IP address: .\deploy -PiAddress 192.168.1.50"
    exit 1
}

# Step 2: copy the files.
Write-Host "Step 2 of 4: Copying files..."
$Items = @(Get-ChildItem $LocalDir | Where-Object { $_.Name -ne "__pycache__" } | ForEach-Object { $_.FullName })
scp -q -r -o ConnectTimeout=10 $Items "${Target}:$RemoteDir/"
if ($LASTEXITCODE -ne 0) {
    Write-Host "The copy didn't finish. Nothing is broken, so it's safe to run this again." -ForegroundColor Yellow
    exit 1
}

# Step 3: install anything missing. Packages already installed are skipped.
Write-Host "Step 3 of 4: Checking the Pi has what it needs..."
foreach ($Package in $Packages) {
    ssh -n $Target "dpkg -s $Package >/dev/null 2>&1"
    if ($LASTEXITCODE -ne 0) {
        ssh -t $Target "sudo apt install -y $Package"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Couldn't install $Package on the Pi. Your files were copied. Is the Pi online?" -ForegroundColor Yellow
            exit 1
        }
    }
}

# Step 4: start Jarvis with the new code. It also starts by itself when the Pi turns on.
# Restarting relaxes the servos, but starting Jarvis never moves the arm.
Write-Host "Step 4 of 4: Restarting the Jarvis page..."
# Jarvis uses its own Python environment for the anthropic library. The first run downloads it.
$Venv = "~/.local/share/jarvis/venv"
ssh -n $Target "test -x $Venv/bin/python || python3 -m venv --system-site-packages $Venv; $Venv/bin/python -c 'import anthropic' 2>/dev/null || $Venv/bin/pip install --quiet 'anthropic>=1.17,<2'"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Your files were copied, but the chat library didn't install. Is the Pi online?" -ForegroundColor Yellow
    exit 1
}
ssh -n $Target "mkdir -p ~/.config/systemd/user && cp ~/$RemoteDir/jarvis.service ~/.config/systemd/user/jarvis.service && systemctl --user daemon-reload && systemctl --user enable --quiet jarvis && loginctl enable-linger && systemctl --user restart jarvis && sleep 2 && systemctl --user is-active --quiet jarvis"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Your files were copied, but Jarvis didn't start. Nothing moved. Share this message with Claude." -ForegroundColor Yellow
    exit 1
}

Write-Host "Deployed! Your files are in ~/$RemoteDir on the Pi." -ForegroundColor Green
Write-Host "Jarvis is at http://${PiAddress}:8000" -ForegroundColor Green

if ($Run) {
    Write-Host ""
    Write-Host "Running $Run on the Pi. Press Ctrl+C to stop it."
    ssh -t $Target "cd ~/$RemoteDir && python3 -u '$Run'"
    exit $LASTEXITCODE
}
