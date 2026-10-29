#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$ROOT/.tools/dotnet"

if [[ -x "$INSTALL_DIR/dotnet" ]] && "$INSTALL_DIR/dotnet" --list-sdks | awk '{split($1, v, "."); if (v[1] ~ /^[0-9]+$/ && v[1] >= 8) found=1} END {exit !found}'; then
    echo "An appropriate local .NET SDK is already installed."
    "$INSTALL_DIR/dotnet" --list-sdks
    exit 0
fi

if command -v curl >/dev/null 2>&1; then
    DOWNLOAD=(curl -fLsS --retry 3 -o)
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD=(wget -q -O)
else
    echo "Error: curl or wget is required to download the official .NET installer." >&2
    exit 1
fi

INSTALL_SCRIPT="$(mktemp)"
trap 'rm -f "$INSTALL_SCRIPT"' EXIT

echo "Downloading the official Microsoft .NET SDK installer..."
"${DOWNLOAD[@]}" "$INSTALL_SCRIPT" "https://dot.net/v1/dotnet-install.sh"

echo "Installing .NET SDK 8 into .tools/dotnet (no sudo required)..."
# Use an isolated SDK directory and leave the system installation unchanged.
bash "$INSTALL_SCRIPT" --channel 8.0 --install-dir "$INSTALL_DIR" --no-path

if ! "$INSTALL_DIR/dotnet" --list-sdks | awk '{split($1, v, "."); if (v[1] ~ /^[0-9]+$/ && v[1] >= 8) found=1} END {exit !found}'; then
    echo "Error: No suitable SDK was found after installation." >&2
    exit 1
fi

echo "SDK installation completed. Run ./build.sh to create the mod release."
"$INSTALL_DIR/dotnet" --list-sdks
