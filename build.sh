#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
fi

VERSION="${1:-v3.4.0}"
if [[ -n "${SDTD_DIR:-}" ]]; then
    GAME="$SDTD_DIR"
elif [[ -d "$VERSION" && -f "$VERSION/7DaysToDie_Data/Managed/Assembly-CSharp.dll" ]]; then
    GAME="$(cd "$VERSION" && pwd)"
else
    GAME="${SEVENDTD_VERSIONS_DIR:-$HOME/.7dtd_modmanager/game-versions}/$VERSION"
fi
GAME="${GAME%/}"

for FILE in \
    "$GAME/7DaysToDie_Data/Managed/Assembly-CSharp.dll" \
    "$GAME/7DaysToDie_Data/Managed/LogLibrary.dll" \
    "$GAME/Mods/0_TFP_Harmony/0Harmony.dll"; do
    if [[ ! -f "$FILE" ]]; then
        echo "Error: Required game assembly not found: $FILE" >&2
        echo "Set SDTD_DIR in .env or pass a valid game version to build.sh." >&2
        exit 1
    fi
done

# Prefer the project-local SDK, then fall back to a system installation.
# The SDK is needed only to build the DLL, not to run the game.
if [[ -x "$ROOT/.tools/dotnet/dotnet" ]]; then
    DOTNET="$ROOT/.tools/dotnet/dotnet"
    export DOTNET_ROOT="$ROOT/.tools/dotnet"
elif command -v dotnet >/dev/null 2>&1; then
    DOTNET="$(command -v dotnet)"
else
    echo "Error: A .NET SDK (8 or newer) was not found." >&2
    echo "Run ./setup-dotnet.sh to install the SDK locally without sudo." >&2
    exit 1
fi

if ! "$DOTNET" --list-sdks | awk '{split($1, v, "."); if (v[1] ~ /^[0-9]+$/ && v[1] >= 8) found=1} END {exit !found}'; then
    echo "Error: .NET SDK 8 or newer is required (a runtime alone is not enough)." >&2
    echo "Run ./setup-dotnet.sh or install an SDK globally." >&2
    exit 1
fi

export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_NOLOGO=1

if ! command -v zip >/dev/null 2>&1; then
    echo "Error: The 'zip' command is required." >&2
    exit 1
fi

if [[ -f "$ROOT/Config/items.xml" ]]; then
    echo "Warning: Old Config/items.xml detected. It is not included in the release." >&2
    echo "Warning: Remove that file from any existing installed mod folder." >&2
fi

"$DOTNET" build "$ROOT/Source/FunctionalGasStove.csproj" \
    -c Release -p:Game7D2D="$GAME" -v:minimal

DLL="$ROOT/Source/bin/Release/net48/FunctionalGasStove.dll"
if [[ ! -s "$DLL" ]]; then
    echo "Error: Compiler did not produce the expected DLL: $DLL" >&2
    exit 1
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
MOD="$STAGE/FunctionalGasStove"
mkdir -p "$MOD/Config/XUi_InGame" "$ROOT/releases"
cp "$DLL" "$MOD/FunctionalGasStove.dll"
cp "$ROOT/ModInfo.xml" "$MOD/"
cp "$ROOT/Config/blocks.xml" "$ROOT/Config/recipes.xml" \
   "$ROOT/Config/Localization.csv" "$MOD/Config/"
cp "$ROOT/Config/XUi_InGame/xui.xml" "$MOD/Config/XUi_InGame/"

# Keep previous releases outside the staging directory and do not overwrite them on failure.
OUTPUT="$ROOT/releases/FunctionalGasStove-v1.0.5.zip"
TEMP_OUTPUT="$ROOT/releases/.FunctionalGasStove-v1.0.5.tmp.zip"
rm -f "$TEMP_OUTPUT"
(cd "$STAGE" && zip -q -r "$TEMP_OUTPUT" FunctionalGasStove)
mv -f "$TEMP_OUTPUT" "$OUTPUT"
echo "Build completed: $OUTPUT"
echo "Note: Copy the new release to a clean mod folder to avoid legacy XML files."
