# ============================================================================
# Generate minisign keys for the auto-updater (tauri-plugin-updater).
#
# One-time prerequisite. Run it, then:
#   1. Put the PUBLIC key (the line starting with "RWR" in <name>.pub) into
#      src-tauri/tauri.conf.json -> plugins.updater.pubkey.
#   2. Upload the PRIVATE key contents to GitHub secret MINISIGN_PRIVATE_KEY.
#   3. Upload the password to GitHub secret MINISIGN_PRIVATE_KEY_PASSWORD.
#   4. NEVER commit the private key or the .env into the repo.
#
# Requires Tauri CLI:  cargo install tauri-cli --version ^2
#
# NOTE: messages are ASCII on purpose so the output is not garbled in any
# console codepage.
# ============================================================================

param(
    [string]$Name = "school-kiosk-update.key",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

# Ask for a password only if it was not provided as a parameter.
# The Tauri signer always protects the secret key, so a password is required.
if (-not $Password) {
    $secure = Read-Host "Enter a password to protect the secret key" -AsSecureString
    if (-not $secure) {
        Write-Error "A password is required. Re-run with -Password '<your-password>'."
        exit 1
    }
    $Password = [System.Net.NetworkCredential]::new("", $secure).Password
}

cargo tauri signer generate -w "$Name" -p "$Password"
if ($LASTEXITCODE -ne 0) {
    Write-Error ("Key generation failed (exit code {0}). Make sure Tauri CLI is installed: cargo install tauri-cli --version ^2" -f $LASTEXITCODE)
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Private key saved to: $Name"
Write-Host "Public  key saved to: $Name.pub"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Copy the line starting with RWR from $Name.pub"
Write-Host "     into src-tauri/tauri.conf.json -> plugins.updater.pubkey."
Write-Host "  2. Upload the contents of $Name to GitHub secret MINISIGN_PRIVATE_KEY."
Write-Host "  3. Upload the password you just set to GitHub secret MINISIGN_PRIVATE_KEY_PASSWORD."
Write-Host "  4. Keep $Name and $Name.pub safe; never commit the private key."
