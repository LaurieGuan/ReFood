"""Fridge scan upload endpoint; detections remain unconfirmed candidates."""

from importlib import import_module
from uuid import uuid4

from flask import Blueprint, request, make_response
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, BadGateway, ServiceUnavailable

from schemas.scanning import ScanCandidate, ScanResponse
from .http_utils import json_response

scans_bp = Blueprint("scans", __name__)
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def scan_fridge(image_bytes: bytes) -> list[ScanCandidate]:
    """Call the vision adapter; never fabricate candidates."""
    try:
        scanner = import_module("services.vision").scan_fridge
    except ModuleNotFoundError as exc:
        if exc.name != "services.vision":
            raise
        raise ServiceUnavailable("Vision service is not installed") from exc
    return scanner(image_bytes)


@scans_bp.post("")
def create_scan():
    image = request.files.get("image")
    if image is None:
        raise BadRequest("Expected multipart file field 'image'")
    if not image.mimetype or not image.mimetype.startswith("image/"):
        raise BadRequest("Expected an image upload")

    image_bytes = image.stream.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise RequestEntityTooLarge()
    if not image_bytes:
        raise BadRequest("Image upload is empty")

    try:
        candidates = scan_fridge(image_bytes)
    except ValueError:
        raise BadRequest("Invalid image; upload JPEG, PNG or WebP") from None
    except RuntimeError:
        raise BadGateway("Vision provider unavailable or invalid response; check server configuration and quota") from None
    response = ScanResponse(scan_id=f"scan_{uuid4().hex}", candidates=candidates)
    result = make_response(*json_response(ScanResponse, response))
    result.headers["X-Refood-Source"] = "vision_provider"
    return result
