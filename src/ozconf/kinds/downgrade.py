"""Dev tool: derive draft v0.5 `validate_zarr` cases from the existing v0.6 ones.

OME-Zarr v0.6 (RFC-5) replaced a single implicit per-image coordinate space
with explicit named `coordinateSystems`, and wraps every transform with
`input`/`output` references. v0.5 has no such wrapping: a multiscale has one
flat `axes` list, and per-dataset transforms are a plain list of
`scale`/`translation` objects with no input/output.

`image` is the only kind whose schema actually changed between v0.5 and v0.6,
so it's the only one that needs real structural conversion. `label` and
`plate` are untouched copies (only `ome.version` changes); `well` is a copy
with a path-charset check, since v0.5's path pattern is stricter; `scene` has
no v0.5 equivalent at all.

Cases that exercise v0.6-only capabilities - `identity`/`sequence` dataset
transforms, a multiscale-level transform that isn't scale/translation, or
multiple coordinate systems that can't be resolved to one target - are not
representable in v0.5 and are skipped (reported, not silently dropped).

This is a draft generator, not a faithful migration tool: review its output
before committing it.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from rich import print

from ..case_filter import Case, CaseFilter

logger = logging.getLogger(__name__)

V05_VERSION = "0.5"
ALPHANUMERIC_RE = re.compile(r"^[A-Za-z0-9]+$")
UNSUPPORTED_TRANSFORM_TYPES = {
    "identity",
    "sequence",
    "affine",
    "rotation",
    "mapAxis",
    "byDimension",
}


class NotRepresentable(Exception):
    """Raised when a case relies on a capability with no v0.5 equivalent."""


def _io_name(io: Any) -> str | None:
    """`input`/`output` may be a plain string (older draft) or a {"name"|"path": ...} object."""
    if isinstance(io, str):
        return io
    if isinstance(io, dict):
        return io.get("name") or io.get("path")
    return None


def _strip_io(transform: dict) -> dict:
    return {k: v for k, v in transform.items() if k not in ("input", "output", "name")}


def _downgrade_dataset_transforms(transforms: list) -> list:
    out = []
    for t in transforms:
        if t.get("type") in UNSUPPORTED_TRANSFORM_TYPES:
            raise NotRepresentable(
                f"unsupported dataset transform type {t.get('type')!r}"
            )
        out.append(_strip_io(t))
    return out


def _extract_axes(multiscale: dict) -> list | None:
    coordinate_systems = multiscale.get("coordinateSystems")
    if coordinate_systems is None:
        # already axes-shaped (or missing axes entirely) - pass through as-is
        return multiscale.get("axes")

    target_name = None
    datasets = multiscale.get("datasets") or []
    if datasets:
        transforms = datasets[0].get("coordinateTransformations") or []
        if transforms:
            target_name = _io_name(transforms[0].get("output"))

    cs = next((c for c in coordinate_systems if c.get("name") == target_name), None)
    if cs is None:
        if len(coordinate_systems) == 1:
            cs = coordinate_systems[0]
        else:
            raise NotRepresentable(
                f"can't resolve a single target coordinate system among {len(coordinate_systems)}"
            )

    axes = cs.get("axes")
    if axes is None:
        return None
    return [
        {k: v for k, v in ax.items() if k in ("name", "type", "unit")} for ax in axes
    ]


def _extract_top_transforms(multiscale: dict) -> list | None:
    top = multiscale.get("coordinateTransformations")
    if top is None:
        return None
    out = []
    for t in top:
        if t.get("type") not in ("scale", "translation"):
            raise NotRepresentable(
                f"unsupported multiscale-level transform type {t.get('type')!r}"
            )
        out.append(_strip_io(t))
    return out


def _downgrade_multiscale(multiscale: dict) -> dict:
    out: dict[str, Any] = {}

    axes = _extract_axes(multiscale)
    if axes is not None:
        out["axes"] = axes

    if "datasets" in multiscale:
        datasets = []
        for i, ds in enumerate(multiscale["datasets"]):
            new_ds: dict[str, Any] = {}
            if "path" in ds:
                new_ds["path"] = str(i)
            if "coordinateTransformations" in ds:
                new_ds["coordinateTransformations"] = _downgrade_dataset_transforms(
                    ds["coordinateTransformations"]
                )
            datasets.append(new_ds)
        out["datasets"] = datasets

    top_transforms = _extract_top_transforms(multiscale)
    if top_transforms is not None:
        out["coordinateTransformations"] = top_transforms

    for key in ("name", "type", "metadata"):
        if key in multiscale:
            out[key] = multiscale[key]

    return out


def downgrade_image(ome: dict) -> dict:
    out = dict(ome)
    out["version"] = V05_VERSION
    if "multiscales" in ome:
        out["multiscales"] = [_downgrade_multiscale(ms) for ms in ome["multiscales"]]
    return out


def downgrade_passthrough(ome: dict) -> dict:
    """label and plate: schema is unchanged besides the version string."""
    out = dict(ome)
    out["version"] = V05_VERSION
    return out


def downgrade_well(ome: dict) -> dict:
    images = ome.get("well", {}).get("images", [])
    bad = [
        img["path"]
        for img in images
        if "path" in img and not ALPHANUMERIC_RE.match(img["path"])
    ]
    if bad:
        raise NotRepresentable(
            f"well image path(s) {bad} use characters v0.5's stricter pattern disallows"
        )
    return downgrade_passthrough(ome)


# Dispatch by the first path segment of Case.name - the organisational
# subdirectory under `validity`, e.g. "image/duplicate_axes" -> "image".
KIND_HANDLERS = {
    "image": downgrade_image,
    "label": downgrade_passthrough,
    "plate": downgrade_passthrough,
    "well": downgrade_well,
}


def downgrade_attributes(attributes: dict, case_type: str) -> dict:
    """Takes the `attributes` object of a v0.6 zarr.json; returns the v0.5 equivalent.

    Drops `_conformance` (it's not consumed by ozconf's own runner, and the
    hand-written v0.5 reference cases omit it too). Raises NotRepresentable
    if the case relies on a v0.6-only capability.
    """
    handler = KIND_HANDLERS.get(case_type)
    if handler is None:
        raise NotRepresentable(f"no v0.5 equivalent for kind-type '{case_type}'")
    return {"ome": handler(attributes["ome"])}


def downgrade_case(case: Case, output_root: Path) -> tuple[str, str]:
    """Returns (status, message) where status is 'ok', 'skip', or 'error'."""
    case_type = case.name.split("/")[0]
    with case.as_path() as src_dir:
        zarr_json_path = src_dir / "zarr.json"
        try:
            doc = json.loads(zarr_json_path.read_text())
        except OSError as e:
            return "error", f"couldn't read {zarr_json_path}: {e}"

        try:
            new_attrs = downgrade_attributes(doc["attributes"], case_type)
        except NotRepresentable as e:
            return "skip", str(e)

        dest_dir = output_root / case.profile / case.validity / f"{case.name}.ome.zarr"
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(src_dir, dest_dir)

        new_doc = dict(doc)
        new_doc["attributes"] = new_attrs
        (dest_dir / "zarr.json").write_text(json.dumps(new_doc, indent=2) + "\n")

        return "ok", str(dest_dir)


def run_downgrade(cases: CaseFilter, output_root: Path) -> None:
    """Convert every matching v0.6 `validate_zarr` case to a draft v0.5 case."""
    output_root.mkdir(parents=True, exist_ok=True)
    colour = {"ok": "green", "skip": "yellow", "error": "red"}
    for case, should_run in cases:
        if not should_run or case.version.raw != "v0.6":
            continue
        status, msg = downgrade_case(case, output_root)
        print(
            case.slug(), f"[{colour[status]}]{status}[/{colour[status]}]", msg, sep="\t"
        )
