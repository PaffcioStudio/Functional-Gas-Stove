#!/usr/bin/env python3
"""Validate mod metadata, XML patches, source rules and optional local V3.x files."""

from pathlib import Path
import os
import csv
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
VERSIONS_ROOT = Path(os.environ.get("SEVENDTD_VERSIONS_DIR", str(Path.home() / ".7dtd_modmanager" / "game-versions")))
VERSIONS = ("v3.3.0", "v3.4.0", "latest_experimental")
STOVES = ("cntgasRangeWhite", "cntgasRangeGrey", "cntgasRangeBlack")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def patch_and_validate_blocks(vanilla_xml, patch_xml, version):
    original = ET.parse(vanilla_xml).getroot()
    patch = ET.parse(patch_xml).getroot()
    require(original.tag == "blocks", f"{version}: invalid vanilla blocks.xml")
    for operation in patch:
        target = operation.attrib.get("xpath", "")
        block_match = re.search(r"block\[@name='([^']+)'\]", target)
        require(block_match, "Unsupported XML patch target")
        block_name = block_match.group(1)
        block = original.find(f"./block[@name='{block_name}']")
        require(block is not None, f"{version}: missing block {block_name}")
        if operation.tag == "append":
            for prop in operation:
                block.append(ET.fromstring(ET.tostring(prop)))
        elif operation.tag == "set":
            require(target.endswith("/property[@name='CreativeMode']/@value"), "Unexpected set operation")
            properties = block.findall("./property[@name='CreativeMode']")
            require(len(properties) == 1, f"{version}: invalid CreativeMode target")
            properties[0].set("value", (operation.text or "").strip())
        else:
            raise AssertionError("Unknown patch operation: " + operation.tag)

    for name in STOVES:
        block = original.find(f"./block[@name='{name}']")
        require(len(block.findall("./property[@name='CreativeMode']")) == 1, f"{version}: duplicate CreativeMode in {name}")
        expected = {
            "CreativeMode": "Player",
            "Class": "Campfire",
            "HeatMapStrength": "5",
            "HeatMapTime": "5000",
            "HeatMapFrequency": "1000",
            "ActiveRadiusEffects": "buffCampfireAOE,3",
        }
        for key, value in expected.items():
            props = block.findall(f"./property[@name='{key}']")
            require(len(props) == 1 and props[0].get("value") == value, f"{version}: {name}/{key} mismatch")
    return True


def test_local_version(version):
    path = VERSIONS_ROOT / version
    vanilla = path / "Data/Config/blocks.xml"
    xui = path / "Data/Config/XUi_InGame/xui.xml"
    assembly = path / "7DaysToDie_Data/Managed/Assembly-CSharp.dll"
    if not all(p.is_file() for p in (vanilla, xui, assembly)):
        print(f"{version}: skipped local game validation (game files not found)")
        return

    patch_and_validate_blocks(vanilla, ROOT / "Config/blocks.xml", version)
    vanilla_xui = ET.parse(xui).getroot()
    require(vanilla_xui.find("./window_group[@name='workstation_campfire']") is not None, f"{version}: missing campfire XUi group")
    data = assembly.read_bytes()
    for name in ("TileEntityWorkstation", "getFuelTime", "GetFuelTime", "SetupCategoriesByWorkstation"):
        require(name.encode() + b"\0" in data, f"{version}: missing method/type name {name}")
    print(f"{version}: XML targets and required C# member names verified")


def main():
    modinfo = ET.parse(ROOT / "ModInfo.xml").getroot()
    require(modinfo.find("Name").get("value") == "FunctionalGasStove", "Mod name mismatch")
    require(modinfo.find("Version").get("value") == "1.0.5", "Mod version mismatch")
    require(modinfo.find("Author").get("value") == "Paffcio", "Mod author mismatch")
    for path in (ROOT / "Config").rglob("*.xml"):
        ET.parse(path)
    xui_patch = ET.parse(ROOT / "Config/XUi_InGame/xui.xml").getroot()
    require(len(xui_patch.findall(".//window_group")) == 3, "Expected three workstation UI groups")
    require((ROOT / "image/preview.png").is_file(), "Preview image is missing")
    with (ROOT / "Config/Localization.csv").open(encoding="utf-8", newline="") as localization_file:
        translations = list(csv.DictReader(localization_file))
    require(len(translations) == 6, "Expected six gas stove localization entries")
    require({row["Key"] for row in translations} == {
        f"{name}{suffix}" for name in STOVES for suffix in ("", "Desc")
    }, "Localization keys do not match the three stove variants")
    for row in translations:
        require(row["polish"].strip(), f"Missing Polish translation: {row['Key']}")
        require("," not in row["polish"], f"Comma found in Polish translation: {row['Key']}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("V3.x.x" in readme and "new world" in readme.lower(), "README must document V3.x and new worlds")
    legacy_items = ROOT / "Config/items.xml"
    if legacy_items.exists():
        # Old source folders may contain this file after unpacking over v1.0.4.
        # The release builder deliberately excludes it from the installable mod.
        print("WARNING: Config/items.xml is left over from an older version.")
        print("WARNING: It is excluded from releases. Remove it from any installed mod folder.")
    source = (ROOT / "Source/FunctionalGasStove.cs").read_text(encoding="utf-8")
    for expected in ("GetFuelTime", "getFuelTime", "GasCanBurnSeconds = 300f", "ammoGasCan", "IsGasStove", "SetupCategoriesByWorkstation"):
        require(expected in source, f"Source check failed: {expected}")
    for name in VERSIONS:
        test_local_version(name)
    # Keep prose and shell script output in English and prohibit em dashes in text files.
    for path in ROOT.rglob("*"):
        if not path.is_file() or "releases" in path.parts or path.suffix in (".png", ".dll", ".zip", ".pyc"):
            continue
        if path.name in (".env",) or any(part in ("bin", "obj", ".tools", ".build_stage", "__pycache__") for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8")
        require("\u2014" not in content, f"Em dash U+2014 found in {path.relative_to(ROOT)}")
    build_script = (ROOT / "build.sh").read_text(encoding="utf-8")
    require("releases/FunctionalGasStove-v1.0.5.zip" in build_script, "Release path mismatch")
    require("cp \"$ROOT/Config/blocks.xml\" \"$ROOT/Config/recipes.xml\"" in build_script, "Expected release files are not staged")
    require((ROOT / "setup-dotnet.sh").is_file(), "SDK setup script is missing")
    require("cd \"$STAGE\"" in build_script, "Release should only package staged files")
    print("OK: Metadata, source rules, no em dashes, and release layout")
    print("Note: Static validation does not replace compiling and testing the DLL in-game.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ET.ParseError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
