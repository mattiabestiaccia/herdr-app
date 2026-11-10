#!/usr/bin/env python3
"""Run the real layout, click persistence and atomic-write tests without GPUI/Zig."""
import json
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix="herdr-transparency-tests-") as folder:
    test = Path(folder)
    (test / "src").mkdir()
    (test / "defaults").symlink_to(root / "defaults", target_is_directory=True)
    (test / "Cargo.toml").write_text('''[package]
name = "herdr-transparency-layout-tests"
version = "0.0.0"
edition = "2024"
[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
''')
    modules = [f"#[path = {json.dumps(str(root / 'src' / (name + '.rs')))}]\nmod {name};"
               for name in ("layout", "layout_sync", "persist")]
    (test / "src/lib.rs").write_text("#![allow(dead_code)]\n" + "\n".join(modules) + "\n")
    subprocess.run(["cargo", "test", "--offline", "--manifest-path", str(test / "Cargo.toml")], check=True)
