#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script for Personal Skin Manager using PyInstaller
Fast builds with Windows UI API support
"""

import sys
import subprocess
import shutil
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


MIN_PYTHON = (3, 11)
if sys.version_info < MIN_PYTHON:
    sys.stderr.write(
        f"Personal Skin Manager build scripts require Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer.\n"
        "Please re-run using an updated interpreter.\n"
    )
    sys.exit(1)



def verify_sanitized_build_inputs():
    """Fail closed if retired Rose services/runtime surfaces can enter the build."""
    forbidden_paths = [
        ROOT / "analytics",
        ROOT / "party",
        ROOT / "relay-worker",
        ROOT / "Pengu Loader" / "plugins" / "ROSE-PartyMode",
        ROOT / "vendor" / "PenguLoader-1.1.6" / "loader" / "Main" / "Updater.cs",
    ]
    failures = [f"forbidden path exists: {x.relative_to(ROOT)}" for x in forbidden_paths if x.exists()]
    checks = [
        (ROOT / "vendor/PenguLoader-1.1.6/loader/MainWindow.xaml.cs", "Updater.CheckUpdate(", "inherited updater invocation"),
        (ROOT / "vendor/PenguLoader-1.1.6/loader/Program.cs", "Alban1911/Rose", "loader Rose repository runtime URL"),
        (ROOT / "vendor/PenguLoader-1.1.6/loader/Views/MainPage.xaml", "GitHubButtonClick", "runtime upstream-source button"),
        (ROOT / "vendor/PenguLoader-1.1.6/loader/Views/MainPage.xaml.cs", "Program.GithubIssuesUrl", "Rose GitHub issues redirect"),
        (ROOT / "Pengu Loader/plugins/ROSE-SettingsPanel/index.js", "discord ticket", "legacy Discord support wording"),
    ]
    for file_path, marker, label in checks:
        if not file_path.exists():
            failures.append(f"required file missing: {file_path.relative_to(ROOT)}")
            continue
        text = file_path.read_text(encoding="utf-8-sig")
        if marker.lower() in text.lower():
            failures.append(f"{label} remains in {file_path.relative_to(ROOT)}")
    if failures:
        print("[ERROR] Sanitized build-input verification FAILED:")
        for item in failures:
            print(f"  - {item}")
        return False
    print("[OK] Sanitized build-input verification passed")
    return True

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_step(step_num, total_steps, description):
    """Print a step description"""
    print(f"\n[Step {step_num}/{total_steps}] {description}")
    print("-" * 70)


def clean_previous_builds():
    """Clean previous build output (preserves build/ cache for faster rebuilds)"""
    print_step(1, 4, "Cleaning Previous Build Output")

    # Only clean dist/ - preserve build/ folder for PyInstaller cache
    dirs_to_clean = ["dist"]

    for dir_name in dirs_to_clean:
        directory = ROOT / dir_name
        if directory.exists():
            try:
                shutil.rmtree(directory)
                print(f"[OK] Removed {dir_name}/")
            except Exception as e:
                print(f"[ERROR] Failed to remove {dir_name}/: {e}")

    # Check if build cache exists
    if (ROOT / "build").exists():
        print("[INFO] Preserved build/ folder for faster incremental builds")
    else:
        print("[INFO] No build/ cache found - this will be a full build")

    # Note: injection/ directories are no longer cleaned as they contain real scripts
    # that need to be preserved (tools, config, etc.)

    return True


def build_pengu_loader():
    """Build the vendored Pengu Loader source before packaging Personal Skin Manager."""
    print_step(2, 4, "Building Pengu Loader From Source")

    script = ROOT / "scripts" / "build_pengu_loader.py"
    result = subprocess.run([sys.executable, str(script)], check=False, cwd=ROOT)
    if result.returncode != 0:
        print(f"[ERROR] Pengu Loader source build failed with exit code {result.returncode}")
        return False

    return True


def build_with_pyinstaller():
    """Build executable using PyInstaller with multi-threading"""
    print_step(3, 4, "Building with PyInstaller (Multi-threaded)")

    # Use spec file which has all the configuration
    cmd = [
              sys.executable,
              "-m",
              "PyInstaller",
              "--clean",
              "--noconfirm",
              "PersonalSkinManager.spec",
          ]
    print(f"Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True, cwd=ROOT)
        print("\n[OK] PyInstaller build completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build failed: {e}")
        return False


def organize_output():
    """Organize output files and verify"""
    print_step(4, 4, "Organizing Output & Verification")

    dist_folder = ROOT / "dist/PersonalSkinManager"

    if not dist_folder.exists():
        print("[ERROR] Build output not found!")
        return False

    return True


def main():
    """Main build process"""
    print_header("Personal Skin Manager - PyInstaller Build")

    start_time = time.time()

    # Execute build steps
    if not verify_sanitized_build_inputs():
        sys.exit(1)

    if not clean_previous_builds():
        sys.exit(1)

    if not build_pengu_loader():
        sys.exit(1)

    if not build_with_pyinstaller():
        sys.exit(1)

    if not organize_output():
        print("[WARNING] Verification incomplete, but build may have succeeded")

    # Print summary
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)

    print_header("[OK] BUILD COMPLETED SUCCESSFULLY!")

    exe_path = ROOT / "dist/PersonalSkinManager/PersonalSkinManager.exe"

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"Executable: {exe_path}")
        print(f"Size: {size_mb:.1f} MB")
        print(f"Build time: {minutes}m {seconds}s")

        print(f"\nYour application is ready!")
        print(f"\nMode: STANDALONE (folder with all dependencies)")
        print(f"  - Bundled application dependencies included")
        print(f"  - mod-tools included; cslol-dll.dll supplied separately")

        print(f"\nProtection:")
        print(f"  - Python bytecode (not raw source)")
        print(f"  - Requires decompiler tools to reverse")
        print(f"  - Good enough against casual theft")

        print(f"\nTo test:")
        print(f"  cd dist\\PersonalSkinManager")
        print(f"  PersonalSkinManager.exe")
    else:
        print("[ERROR] Executable not found!")
        sys.exit(1)


if __name__ == "__main__":
    main()
