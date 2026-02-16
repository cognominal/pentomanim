#!/usr/bin/env python3
"""Sync eponymous .md and .mp4 files for Manim scripts.

For each `*.py` in this directory:
- keep `<stem>.md` in sync by writing/replacing an auto-generated metadata block
- regenerate `<stem>.mp4` when stale (or missing), using the first Scene subclass
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

SYNC_START = "<!-- AUTO-SYNC:START -->"
SYNC_END = "<!-- AUTO-SYNC:END -->"
SCENE_BASES = {"Scene", "MovingCameraScene"}
QUALITY_FLAGS = {
    "low": "-ql",
    "medium": "-qm",
    "high": "-qh",
    "production": "-qp",
}


def now_utc() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_scene_name(py_path: Path) -> str | None:
    tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in SCENE_BASES:
                return node.name
            if isinstance(base, ast.Attribute) and base.attr in SCENE_BASES:
                return node.name
    return None


def read_md_source_hash(md_text: str) -> str | None:
    if SYNC_START not in md_text or SYNC_END not in md_text:
        return None
    match = re.search(r"^source_sha256:\s*([a-f0-9]{64})$", md_text, re.MULTILINE)
    return match.group(1) if match else None


def build_sync_block(py_path: Path, scene_name: str | None, quality: str) -> str:
    cmd = f"manim {QUALITY_FLAGS[quality]} {py_path.name}"
    if scene_name:
        cmd += f" {scene_name}"
    return (
        f"{SYNC_START}\n"
        f"source_file: {py_path.name}\n"
        f"source_sha256: {sha256_file(py_path)}\n"
        f"source_mtime_utc: {dt.datetime.fromtimestamp(py_path.stat().st_mtime, tz=dt.timezone.utc).replace(microsecond=0).isoformat()}\n"
        f"synced_at_utc: {now_utc()}\n"
        f"scene: {scene_name or 'N/A'}\n"
        f"render_cmd: {cmd}\n"
        f"{SYNC_END}\n"
    )


def sync_markdown(md_path: Path, py_path: Path, scene_name: str | None, quality: str, dry_run: bool) -> bool:
    new_block = build_sync_block(py_path, scene_name, quality)
    if md_path.exists():
        current = md_path.read_text(encoding="utf-8")
        if SYNC_START in current and SYNC_END in current:
            updated = re.sub(
                rf"{re.escape(SYNC_START)}.*?{re.escape(SYNC_END)}\n?",
                new_block,
                current,
                flags=re.DOTALL,
            )
        else:
            sep = "" if current.endswith("\n") else "\n"
            updated = f"{current}{sep}\n{new_block}"
        changed = updated != current
        if changed and not dry_run:
            md_path.write_text(updated, encoding="utf-8")
        return changed

    title = f"# Spec: `{py_path.name}`\n\n"
    scene_line = f"- `{scene_name}`\n\n" if scene_name else "- `TBD`\n\n"
    body = "## Purpose\n\nDescribe this scene's intent.\n\n## Main Scene\n\n" + scene_line
    content = f"{title}{body}{new_block}"
    if not dry_run:
        md_path.write_text(content, encoding="utf-8")
    return True


def copy_newest_render(stem: str, media_dirs: list[Path], target_mp4: Path, dry_run: bool) -> bool:
    candidates: list[Path] = []
    for media_dir in media_dirs:
        if media_dir.exists():
            candidates.extend(media_dir.glob(f"videos/**/{stem}.mp4"))
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime)
    if not candidates:
        joined = ", ".join(str(d) for d in media_dirs)
        raise FileNotFoundError(f"No rendered mp4 found for stem '{stem}' under: {joined}")
    newest = candidates[-1]
    if dry_run:
        return True
    shutil.copy2(newest, target_mp4)
    return True


def should_render(py_path: Path, mp4_path: Path, md_path: Path) -> bool:
    if not mp4_path.exists() or not md_path.exists():
        return True
    py_mtime = py_path.stat().st_mtime
    return mp4_path.stat().st_mtime < py_mtime or md_path.stat().st_mtime < py_mtime


def run_manim(py_path: Path, scene_name: str, quality: str, dry_run: bool) -> None:
    if dry_run:
        return
    cmd = ["manim", QUALITY_FLAGS[quality], str(py_path), scene_name, "-o", py_path.stem]
    # Force Manim output under the script directory's media tree for stable discovery.
    subprocess.run(cmd, check=True, cwd=str(py_path.parent))


def process_file(
    py_path: Path,
    quality: str,
    dry_run: bool,
    skip_render: bool,
    skip_non_scene: bool,
) -> tuple[bool, bool, bool]:
    stem = py_path.stem
    md_path = py_path.with_suffix(".md")
    mp4_path = py_path.with_suffix(".mp4")
    scene_name = first_scene_name(py_path)
    if scene_name is None and skip_non_scene:
        return False, False, True

    py_hash = sha256_file(py_path)

    md_changed = False
    if not md_path.exists():
        md_changed = sync_markdown(md_path, py_path, scene_name, quality, dry_run)
    else:
        existing = md_path.read_text(encoding="utf-8")
        md_hash = read_md_source_hash(existing)
        if md_hash != py_hash:
            md_changed = sync_markdown(md_path, py_path, scene_name, quality, dry_run)

    rendered = False
    if not skip_render and should_render(py_path, mp4_path, md_path):
        if scene_name is None:
            raise ValueError(f"No Scene subclass found in {py_path.name}; cannot render mp4")
        run_manim(py_path, scene_name, quality, dry_run)
        copy_newest_render(
            stem,
            [py_path.parent / "media", Path.cwd() / "media"],
            mp4_path,
            dry_run,
        )
        rendered = True
    return md_changed, rendered, False


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory to scan for .py files (default: script directory).",
    )
    parser.add_argument(
        "--quality",
        choices=sorted(QUALITY_FLAGS.keys()),
        default="high",
        help="Manim render quality for regenerated mp4 files.",
    )
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Only process specific script filename(s), e.g. --file triplication_dfs_tree.py",
    )
    parser.add_argument(
        "--skip-non-scene",
        action="store_true",
        default=True,
        help="Skip python files that do not define a Scene subclass (default: true).",
    )
    parser.add_argument(
        "--no-skip-non-scene",
        action="store_false",
        dest="skip_non_scene",
        help="Treat non-scene python files as errors.",
    )
    parser.add_argument("--skip-render", action="store_true", help="Only sync markdown files.")
    parser.add_argument("--dry-run", action="store_true", help="Show intended work without writing or rendering.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    target_dir = args.dir.resolve()

    files = [target_dir / name for name in args.file] if args.file else sorted(target_dir.glob("*.py"))
    files = [p for p in files if p.is_file() and p.name != Path(__file__).name]
    if not files:
        print("No python files to process.")
        return 0

    md_updates = 0
    mp4_updates = 0
    skipped_non_scene = 0
    for py_path in files:
        try:
            md_changed, rendered, skipped = process_file(
                py_path,
                args.quality,
                args.dry_run,
                args.skip_render,
                args.skip_non_scene,
            )
            skipped_non_scene += int(skipped)
            md_updates += int(md_changed)
            mp4_updates += int(rendered)
            status = []
            if skipped:
                status.append("skipped(non-scene)")
            if md_changed:
                status.append("md-updated")
            if rendered:
                status.append("mp4-updated")
            if not status:
                status.append("up-to-date")
            print(f"{py_path.name}: {', '.join(status)}")
        except Exception as exc:  # pragma: no cover
            print(f"{py_path.name}: ERROR: {exc}", file=sys.stderr)
            return 1

    print(f"Done. markdown={md_updates}, mp4={mp4_updates}, skipped_non_scene={skipped_non_scene}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
