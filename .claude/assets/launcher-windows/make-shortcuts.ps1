# Creates the two desktop shortcuts.
#
# Only run this if the person actually asked for it — it writes outside the
# vault, which nothing else in this project does.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File make-shortcuts.ps1 `
#       -VaultPath "C:\path\to\vault" -Name "Jarvis"
#
# -Destination defaults to the Desktop; pass a folder to put them elsewhere.

param(
  [Parameter(Mandatory = $true)][string]$VaultPath,
  [Parameter(Mandatory = $true)][string]$Name,
  [string]$StartFile = "Start Jarvis.bat",
  [string]$StopFile  = "Stop Jarvis.bat",
  [string]$Destination = [Environment]::GetFolderPath("Desktop"),
  [string]$StartLabel,
  [string]$StopLabel
)

if (-not $StartLabel) { $StartLabel = "Start $Name" }
if (-not $StopLabel)  { $StopLabel  = "Stop $Name" }

$VaultPath = (Resolve-Path $VaultPath).Path
if (-not (Test-Path $Destination)) { throw "Destination folder not found: $Destination" }

$pairs = @(
  @{ Target = Join-Path $VaultPath $StartFile; Link = Join-Path $Destination "$StartLabel.lnk" },
  @{ Target = Join-Path $VaultPath $StopFile;  Link = Join-Path $Destination "$StopLabel.lnk"  }
)

foreach ($p in $pairs) {
  if (-not (Test-Path $p.Target)) { throw "Missing launcher: $($p.Target)" }
}

$shell = New-Object -ComObject WScript.Shell
foreach ($p in $pairs) {
  $sc = $shell.CreateShortcut($p.Link)
  $sc.TargetPath       = $p.Target
  $sc.WorkingDirectory = $VaultPath
  $sc.WindowStyle      = 7          # minimised, so the console barely flashes
  $sc.Description      = "$Name"
  $sc.Save()
  Write-Host "created: $($p.Link)"
}
