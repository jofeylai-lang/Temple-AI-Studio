from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_IDENTITY_ID = "emma"
DEFAULT_THRESHOLD = 0.9


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def project_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    allowed = []
    for char in value.lower().strip():
        if char.isalnum() or char in "-_":
            allowed.append(char)
        elif char.isspace():
            allowed.append("-")
    return "".join(allowed).strip("-") or "reference"


def identity_paths(root: Path, identity_id: str) -> dict[str, Path]:
    return {
        "profile": root / "avatar" / "identity" / f"{identity_id}.identity.json",
        "fingerprint": root / "avatar" / "identity" / f"{identity_id}.fingerprint.json",
        "references": root / "avatar" / "references" / identity_id,
        "reports": root / "evaluations" / "quality-reviews" / "emma-identity",
    }


def default_profile(identity_id: str) -> dict:
    return {
        "schema": "temple-ai-studio.emma-identity-profile.v1",
        "identityId": identity_id,
        "displayName": "Emma",
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
        "status": "needs-approved-reference-material",
        "permanent": {
            "face": "same face",
            "body": "same body",
            "voice": "same voice",
            "identity": "same identity",
            "continuity": "same core character continuity",
        },
        "mutable": [
            "clothing",
            "hairstyle",
            "accessories",
            "scene",
            "pose",
            "expression",
            "lighting",
            "camera language",
        ],
        "referencePolicy": {
            "requiresCeoApprovedMaterial": True,
            "doNotInventPermanentIdentity": True,
            "privateReferenceMediaIsNotCommittedToGit": True,
        },
        "references": [],
    }


def load_json(path: Path, fallback: dict | None = None) -> dict:
    if not path.exists():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def init_identity(root: Path, identity_id: str) -> dict:
    paths = identity_paths(root, identity_id)
    ensure_dir(paths["references"])
    profile = load_json(paths["profile"], default_profile(identity_id))
    profile.setdefault("references", [])
    profile["updatedAt"] = now_iso()
    write_json(paths["profile"], profile)
    return {"ok": True, "profile": str(paths["profile"]), "references": str(paths["references"]), "referenceCount": len(profile["references"])}


def image_average_rgb(image: Image.Image) -> list[int]:
    small = image.convert("RGB").resize((1, 1))
    return list(small.getpixel((0, 0)))


def image_luma(rgb: list[int]) -> float:
    return round((0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255, 4)


def average_hash(image: Image.Image, size: int = 8) -> str:
    gray = image.convert("L").resize((size, size))
    pixels = list(gray.tobytes())
    avg = sum(pixels) / len(pixels)
    bits = ["1" if pixel >= avg else "0" for pixel in pixels]
    return bits_to_hex(bits)


def difference_hash(image: Image.Image, size: int = 8) -> str:
    gray = image.convert("L").resize((size + 1, size))
    bits = []
    for y in range(size):
        for x in range(size):
            left = gray.getpixel((x, y))
            right = gray.getpixel((x + 1, y))
            bits.append("1" if left > right else "0")
    return bits_to_hex(bits)


def bits_to_hex(bits: list[str]) -> str:
    value = int("".join(bits), 2)
    width = len(bits) // 4
    return f"{value:0{width}x}"


def hamming_hex(left: str, right: str) -> int:
    width = max(len(left), len(right))
    left_int = int(left.zfill(width), 16)
    right_int = int(right.zfill(width), 16)
    return (left_int ^ right_int).bit_count()


def analyze_image(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = image_average_rgb(image)
        width, height = image.size
        return {
            "path": str(path),
            "sha256": sha256_file(path),
            "fileName": path.name,
            "format": image.format,
            "width": width,
            "height": height,
            "aspectRatio": round(width / height, 4) if height else None,
            "averageRgb": rgb,
            "averageLuma": image_luma(rgb),
            "averageHash": average_hash(image),
            "differenceHash": difference_hash(image),
        }


def import_reference(root: Path, identity_id: str, source: Path, kind: str, label: str, approved_by: str) -> dict:
    if source.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image extension: {source.suffix}")
    if not source.exists():
        raise FileNotFoundError(str(source))

    init_identity(root, identity_id)
    paths = identity_paths(root, identity_id)
    profile = load_json(paths["profile"])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = paths["references"] / f"{stamp}-{safe_name(kind)}-{safe_name(label)}{source.suffix.lower()}"
    ensure_dir(destination.parent)
    shutil.copy2(source, destination)

    analysis = analyze_image(destination)
    reference = {
        "id": f"ref-{stamp}-{safe_name(label)}",
        "kind": kind,
        "label": label,
        "approvedBy": approved_by,
        "importedAt": now_iso(),
        "image": analysis,
    }
    profile.setdefault("references", []).append(reference)
    profile["status"] = "reference-material-present"
    profile["updatedAt"] = now_iso()
    write_json(paths["profile"], profile)
    fingerprint = build_fingerprint(root, identity_id)
    return {"ok": True, "reference": reference, "fingerprint": fingerprint}


def build_fingerprint(root: Path, identity_id: str) -> dict:
    paths = identity_paths(root, identity_id)
    profile = load_json(paths["profile"], default_profile(identity_id))
    references = profile.get("references", [])
    visual_refs = [ref for ref in references if "image" in ref]
    payload = {
        "schema": "temple-ai-studio.emma-identity-fingerprint.v1",
        "identityId": identity_id,
        "displayName": profile.get("displayName", "Emma"),
        "createdAt": now_iso(),
        "referenceCount": len(visual_refs),
        "status": "ready" if visual_refs else "blocked-missing-reference-material",
        "threshold": DEFAULT_THRESHOLD,
        "references": [
            {
                "id": ref["id"],
                "kind": ref["kind"],
                "label": ref["label"],
                "sha256": ref["image"]["sha256"],
                "averageHash": ref["image"]["averageHash"],
                "differenceHash": ref["image"]["differenceHash"],
                "averageRgb": ref["image"]["averageRgb"],
                "averageLuma": ref["image"]["averageLuma"],
                "aspectRatio": ref["image"]["aspectRatio"],
            }
            for ref in visual_refs
        ],
    }
    write_json(paths["fingerprint"], payload)
    return {"path": str(paths["fingerprint"]), "status": payload["status"], "referenceCount": payload["referenceCount"]}


def color_similarity(a: list[int], b: list[int]) -> float:
    distance = sum((a[index] - b[index]) ** 2 for index in range(3)) ** 0.5
    max_distance = (255 ** 2 * 3) ** 0.5
    return max(0.0, 1.0 - distance / max_distance)


def aspect_similarity(a: float | None, b: float | None) -> float:
    if not a or not b:
        return 0.0
    return max(0.0, 1.0 - min(abs(a - b) / max(a, b), 1.0))


def compare_to_reference(candidate: dict, reference: dict) -> dict:
    ah_distance = hamming_hex(candidate["averageHash"], reference["averageHash"])
    dh_distance = hamming_hex(candidate["differenceHash"], reference["differenceHash"])
    ah_similarity = 1.0 - ah_distance / 64
    dh_similarity = 1.0 - dh_distance / 64
    rgb_similarity = color_similarity(candidate["averageRgb"], reference["averageRgb"])
    ar_similarity = aspect_similarity(candidate["aspectRatio"], reference["aspectRatio"])
    score = round((ah_similarity * 0.35) + (dh_similarity * 0.35) + (rgb_similarity * 0.15) + (ar_similarity * 0.15), 4)
    return {
        "referenceId": reference["id"],
        "referenceKind": reference["kind"],
        "referenceLabel": reference["label"],
        "score": score,
        "averageHashSimilarity": round(ah_similarity, 4),
        "differenceHashSimilarity": round(dh_similarity, 4),
        "colorSimilarity": round(rgb_similarity, 4),
        "aspectSimilarity": round(ar_similarity, 4),
    }


def evaluate_candidate(root: Path, identity_id: str, candidate: Path, output: Path | None = None) -> dict:
    paths = identity_paths(root, identity_id)
    fingerprint = load_json(paths["fingerprint"])
    candidate_analysis = analyze_image(candidate)
    references = fingerprint.get("references", [])
    if not references:
        report = {
            "schema": "temple-ai-studio.emma-identity-evaluation.v1",
            "createdAt": now_iso(),
            "identityId": identity_id,
            "overall": "BLOCKED",
            "reason": "No approved Emma reference material exists.",
            "candidate": candidate_analysis,
            "matches": [],
        }
    else:
        matches = [compare_to_reference(candidate_analysis, ref) for ref in references]
        best = max(matches, key=lambda item: item["score"])
        threshold = float(fingerprint.get("threshold", DEFAULT_THRESHOLD))
        report = {
            "schema": "temple-ai-studio.emma-identity-evaluation.v1",
            "createdAt": now_iso(),
            "identityId": identity_id,
            "overall": "PASS" if best["score"] >= threshold else "FAIL",
            "threshold": threshold,
            "candidate": candidate_analysis,
            "bestMatch": best,
            "matches": sorted(matches, key=lambda item: item["score"], reverse=True),
            "note": "This V1 core uses local perceptual fingerprints. It is a first identity gate, not final face recognition.",
        }
    if output:
        write_json(output, report)
    return report


def status(root: Path, identity_id: str) -> dict:
    paths = identity_paths(root, identity_id)
    profile = load_json(paths["profile"], default_profile(identity_id))
    fingerprint = load_json(paths["fingerprint"])
    return {
        "identityId": identity_id,
        "profileExists": paths["profile"].exists(),
        "fingerprintExists": paths["fingerprint"].exists(),
        "referenceDir": str(paths["references"]),
        "referenceCount": len(profile.get("references", [])),
        "profileStatus": profile.get("status"),
        "fingerprintStatus": fingerprint.get("status", "missing"),
    }


def self_test() -> dict:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "source.png"
        candidate = root / "candidate.png"
        different = root / "different.png"
        make_test_image(source, (210, 170, 145), "A")
        make_test_image(candidate, (212, 172, 146), "A")
        make_test_image(different, (30, 80, 210), "B")
        init_identity(root, "self-test-emma")
        import_reference(root, "self-test-emma", source, "face", "self-test-reference", "self-test")
        pass_report = evaluate_candidate(root, "self-test-emma", candidate)
        fail_report = evaluate_candidate(root, "self-test-emma", different)
        return {
            "schema": "temple-ai-studio.emma-identity-self-test.v1",
            "createdAt": now_iso(),
            "overall": "PASS" if pass_report["overall"] == "PASS" and fail_report["overall"] == "FAIL" else "FAIL",
            "similarCandidate": pass_report["overall"],
            "differentCandidate": fail_report["overall"],
            "similarScore": pass_report.get("bestMatch", {}).get("score"),
            "differentScore": fail_report.get("bestMatch", {}).get("score"),
        }


def make_test_image(path: Path, rgb: tuple[int, int, int], label: str) -> None:
    image = Image.new("RGB", (512, 768), rgb)
    draw = ImageDraw.Draw(image)
    if label == "B":
        draw.rectangle((90, 90, 420, 275), fill=tuple(min(255, channel + 45) for channel in rgb))
        draw.ellipse((160, 360, 350, 690), fill=tuple(max(0, channel - 65) for channel in rgb))
        draw.line((80, 720, 430, 120), fill=(255, 255, 255), width=12)
    else:
        draw.ellipse((156, 110, 356, 310), fill=tuple(min(255, channel + 25) for channel in rgb))
        draw.rectangle((180, 330, 332, 650), fill=tuple(max(0, channel - 35) for channel in rgb))
        draw.text((230, 360), label, fill=(255, 255, 255))
    image.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Emma Identity Core.")
    parser.add_argument("--root", default=str(project_root_from_script()), help="Project root path.")
    parser.add_argument("--identity-id", default=DEFAULT_IDENTITY_ID, help="Identity id, default: emma.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("build-fingerprint")
    self_test_parser = sub.add_parser("self-test")
    self_test_parser.add_argument("--output", help="Optional JSON report output path")

    import_parser = sub.add_parser("import-reference")
    import_parser.add_argument("--source", required=True)
    import_parser.add_argument("--kind", required=True, choices=["face", "body", "style", "expression", "pose", "outfit"])
    import_parser.add_argument("--label", required=True)
    import_parser.add_argument("--approved-by", default="CEO")

    evaluate_parser = sub.add_parser("evaluate-image")
    evaluate_parser.add_argument("--candidate", required=True)
    evaluate_parser.add_argument("--output")

    args = parser.parse_args()
    root = Path(args.root)
    if args.command == "init":
        result = init_identity(root, args.identity_id)
    elif args.command == "status":
        result = status(root, args.identity_id)
    elif args.command == "build-fingerprint":
        result = build_fingerprint(root, args.identity_id)
    elif args.command == "import-reference":
        result = import_reference(root, args.identity_id, Path(args.source), args.kind, args.label, args.approved_by)
    elif args.command == "evaluate-image":
        output = Path(args.output) if args.output else None
        result = evaluate_candidate(root, args.identity_id, Path(args.candidate), output)
    elif args.command == "self-test":
        result = self_test()
        if args.output:
            write_json(Path(args.output), result)
    else:
        raise ValueError(args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("overall", "PASS") in ["PASS", "BLOCKED"] or result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
