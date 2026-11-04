# EXAMPLE to adapt (not part of the hueman product).
# What it does: reads a JSON file with the keys "fill" and "text" (#RRGGBB),
# validates them and updates the styles of the Windhawk
# "windows-11-taskbar-styler" mod in the registry; reloads the mod only if a
# color changed.
# Requires elevation: it writes under HKLM. Meant to run from a scheduled task
# with RunLevel Highest (see install-windhawk-taskbar-task.ps1).
# Not tested in this repo: review the script before running it.
<#
.SYNOPSIS
  Applies taskbar colors to the Windhawk "windows-11-taskbar-styler" mod.
.DESCRIPTION
  Reads a JSON data file with keys "fill" and "text" (#RRGGBB), validates them
  strictly, updates the matching style values under the mod's Settings key and
  reloads the mod (Disabled=1, wait, Disabled=0) only if something changed.
  The data file is treated strictly as data. Only the mod's own key is touched.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DataFile
)

$ErrorActionPreference = 'Stop'

$ModKey      = 'HKLM:\SOFTWARE\Windhawk\Engine\Mods\windows-11-taskbar-styler'
$SettingsKey = "$ModKey\Settings"
$HexRegex    = '^#[0-9A-Fa-f]{6}$'

$data = Get-Content -LiteralPath $DataFile -Raw -Encoding UTF8 | ConvertFrom-Json

foreach ($name in 'fill', 'text') {
    $v = $data.$name
    if (($v -isnot [string]) -or ($v -notmatch $HexRegex)) {
        throw "Invalid or missing '$name' in data file: expected #RRGGBB."
    }
}

$fill = '#FF' + $data.fill.Substring(1).ToUpperInvariant()
$text = '#FF' + $data.text.Substring(1).ToUpperInvariant()

if (-not (Test-Path -LiteralPath $SettingsKey)) {
    throw "Windhawk mod settings key not found: $SettingsKey"
}

$props = Get-ItemProperty -LiteralPath $SettingsKey
$changed = $false

foreach ($prop in $props.PSObject.Properties) {
    if ($prop.Name -notmatch '^controlStyles\[\d+\]\.styles\[0\]$') { continue }
    if ($prop.Value -isnot [string]) { continue }

    $new = $null
    if ($prop.Value -match '^Fill=#[0-9A-Fa-f]{8}$') {
        $new = "Fill=$fill"
    }
    elseif ($prop.Value -match '^Foreground=#[0-9A-Fa-f]{8}$') {
        $new = "Foreground=$text"
    }
    else {
        continue
    }

    if ($new -cne $prop.Value) {
        Set-ItemProperty -LiteralPath $SettingsKey -Name $prop.Name -Value $new -Type String
        $changed = $true
        Write-Output "Updated $($prop.Name): $($prop.Value) -> $new"
    }
}

if ($changed) {
    Set-ItemProperty -LiteralPath $ModKey -Name 'Disabled' -Value 1 -Type DWord
    Start-Sleep -Seconds 2
    Set-ItemProperty -LiteralPath $ModKey -Name 'Disabled' -Value 0 -Type DWord
    Write-Output 'Windhawk mod reloaded.'
}
else {
    Write-Output 'No changes; mod not reloaded.'
}
