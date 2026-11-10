#!/usr/bin/env python3
"""Prepare and operate only the isolated desktop-transparency prototype."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
STATE = Path.home() / "personal/tools/herdr-transparency-state"
LAYOUT = "herdr-transparent"


def environment(state=STATE):
    env = dict(os.environ)
    for name in list(env):
        if name.startswith(("HC_", "HERDR_")):
            env.pop(name)
    tag = hashlib.sha256(str(state.resolve()).encode()).hexdigest()[:8]
    runtime = Path("/tmp") / f"htr-{os.getuid()}-{tag}"
    env.update(HERDR_APP_HOME=str(state / "home"), HC_SESSION=f"test-glass-{tag}",
               HERDR_APP_ID="herdr-transparency-prototype",
               XDG_CONFIG_HOME=str(state / "config"), XDG_STATE_HOME=str(runtime / "state"),
               XDG_CACHE_HOME=str(state / "cache"), XDG_RUNTIME_DIR=str(runtime),
               HERDR_APP_NO_SOUND="1")
    return env


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(value, out, indent=2, allow_nan=False)
            out.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def prepare(state=STATE):
    env = environment(state)
    for key in ("HERDR_APP_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    home = Path(env["HERDR_APP_HOME"])
    layout = home / f"layouts/{LAYOUT}.json"
    if not layout.exists():
        write_json(layout, json.loads((Path(__file__).parent / f"{LAYOUT}.json").read_text()))
    settings = home / "settings.json"
    if not settings.exists():
        write_json(settings, {"telemetry": False})
    shared = home / "shared.json"
    if not shared.exists():
        write_json(shared, {"layout": LAYOUT})
    return env


def set_background(mode, opacity, state=STATE):
    if mode not in ("opaque", "transparent", "blurred") or not math.isfinite(opacity) or not 0 <= opacity <= 1:
        raise ValueError("mode: opaque/transparent/blurred; opacity: finite number in 0..1")
    env = prepare(state)
    layout = Path(env["HERDR_APP_HOME"]) / f"layouts/{LAYOUT}.json"
    value = json.loads(layout.read_text())
    value.update(background_mode=mode, workspace_opacity=opacity)
    write_json(layout, value)


def bundle(binary):
    if sys.platform != "darwin":
        raise ValueError("the prototype bundle requires macOS")
    if not binary.is_file():
        raise ValueError(f"build the app first: missing {binary}")
    app = ROOT / "dist/Herdr Transparency.app"
    macos = app / "Contents/MacOS"
    resources = app / "Contents/Resources"
    macos.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)
    target = macos / "Herdr-Transparency"
    shutil.copy2(binary, target)
    target.chmod(0o755)
    launcher = macos / "launch"
    search_path = os.pathsep.join([str(Path.home() / ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin"])
    launcher.write_text("#!/bin/sh\n" +
                        f'export PATH={shlex.quote(search_path)}:"${{PATH:-/usr/bin:/bin}}"\n' +
                        'here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n' +
                        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))} " +
                        '--bin "$here/Herdr-Transparency" run\n')
    launcher.chmod(0o755)
    shutil.copy2(ROOT / "assets/icons/Herdr.icns", resources / "Herdr.icns")
    for name in ("LICENSE", "THIRD-PARTY-NOTICES"):
        shutil.copy2(ROOT / name, resources / name)
    info = dict(CFBundleExecutable="launch", CFBundleIdentifier="personal.herdr.transparency.prototype",
                CFBundleName="Herdr Transparency", CFBundleDisplayName="Herdr Transparency",
                CFBundlePackageType="APPL", CFBundleIconFile="Herdr", CFBundleVersion="1",
                CFBundleShortVersionString="0.1", NSHighResolutionCapable=True)
    with (app / "Contents/Info.plist").open("wb") as out:
        plistlib.dump(info, out)
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, default=ROOT / "target/debug/herdr-app")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("run")
    sub.add_parser("bundle")
    select = sub.add_parser("set")
    select.add_argument("mode", choices=("opaque", "transparent", "blurred"))
    select.add_argument("opacity", type=float)
    cli = sub.add_parser("cli")
    cli.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    binary = args.bin.resolve()
    if args.command == "set":
        set_background(args.mode, args.opacity)
    elif args.command == "prepare":
        print(prepare()["HERDR_APP_HOME"])
    elif args.command == "bundle":
        print(bundle(binary))
    else:
        if not binary.is_file():
            parser.error(f"build the app first: missing {binary}")
        if not shutil.which("hc"):
            parser.error("hc must be installed before running the prototype")
        env = prepare()
        argv = args.args if args.command == "cli" else []
        if args.command == "cli" and not argv:
            parser.error("cli requires an app subcommand, e.g. status")
        os.execve(binary, [str(binary), *argv], env)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        sys.exit(str(error))
