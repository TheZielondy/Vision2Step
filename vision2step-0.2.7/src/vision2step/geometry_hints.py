"""Conservative local silhouette measurements used to ground Claude's analysis."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from io import BytesIO
from statistics import median

from PIL import Image

from vision2step.models import EnclosedRegionHint, GeometryHintRecord


@dataclass(frozen=True)
class HoleHint:
    """Normalized bounding box for an enclosed background region."""

    center_x: float
    center_y: float
    width: float
    height: float
    area_fraction: float

    def as_prompt_line(self, index: int) -> str:
        return (
            f"enclosed_region_{index}: center=({self.center_x:.3f}, {self.center_y:.3f}); "
            f"size=({self.width:.3f} width, {self.height:.3f} height); "
            f"area_fraction={self.area_fraction:.4f}"
        )


@dataclass(frozen=True)
class GeometryHints:
    """Normalized foreground geometry derived without using model tokens."""

    raster_width: int
    raster_height: int
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    object_aspect_ratio: float
    dominant_axis: str
    foreground_fill_ratio: float
    enclosed_regions: tuple[HoleHint, ...]
    confidence: str

    def as_prompt_text(self, image_number: int) -> str:
        lines = [
            f"Reference image {image_number} deterministic measurements:",
            f"- analysis raster: {self.raster_width} x {self.raster_height} px",
            (
                f"- foreground bbox: x={self.bbox_x}, y={self.bbox_y}, "
                f"width={self.bbox_width}, height={self.bbox_height} px"
            ),
            f"- foreground width/height ratio: {self.object_aspect_ratio:.3f}",
            f"- dominant image axis: {self.dominant_axis}",
            f"- foreground fill within bbox: {self.foreground_fill_ratio:.3f}",
            f"- segmentation confidence: {self.confidence}",
        ]
        if self.enclosed_regions:
            lines.append(
                "- enclosed background regions, normalized to foreground bbox "
                "(origin top-left; x right; y down):"
            )
            lines.extend(
                f"  - {region.as_prompt_line(index)}"
                for index, region in enumerate(self.enclosed_regions, start=1)
            )
        else:
            lines.append("- no reliable enclosed background region detected")
        return "\n".join(lines)

    def as_record(self, image_number: int, file_name: str) -> GeometryHintRecord:
        """Convert runtime measurements into the persisted analyzer contract."""

        return GeometryHintRecord(
            image_number=image_number,
            file_name=file_name,
            raster_width=self.raster_width,
            raster_height=self.raster_height,
            bbox_x=self.bbox_x,
            bbox_y=self.bbox_y,
            bbox_width=self.bbox_width,
            bbox_height=self.bbox_height,
            object_aspect_ratio=self.object_aspect_ratio,
            dominant_axis=self.dominant_axis,
            foreground_fill_ratio=self.foreground_fill_ratio,
            enclosed_regions=[
                EnclosedRegionHint(
                    center_x=region.center_x,
                    center_y=region.center_y,
                    width=region.width,
                    height=region.height,
                    area_fraction=region.area_fraction,
                )
                for region in self.enclosed_regions
            ],
            confidence=self.confidence,
        )


def extract_geometry_hints(image_bytes: bytes, *, max_edge: int = 1000) -> GeometryHints | None:
    """Measure a high-contrast foreground conservatively; return None when unreliable."""

    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGB")
    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    width, height = image.size
    if width < 8 or height < 8:
        return None

    flattened = getattr(image, "get_flattened_data", None)
    pixels = list(flattened() if flattened is not None else image.getdata())
    border_indices = set(range(width))
    border_indices.update(range((height - 1) * width, height * width))
    border_indices.update(row * width for row in range(height))
    border_indices.update(row * width + width - 1 for row in range(height))
    border = [pixels[index] for index in border_indices]
    background = tuple(int(median(pixel[channel] for pixel in border)) for channel in range(3))
    border_deviation = sum(
        max(abs(pixel[channel] - background[channel]) for channel in range(3))
        for pixel in border
    ) / len(border)
    threshold = min(80, max(24, int(border_deviation * 4)))

    mask = bytearray(
        max(abs(pixel[channel] - background[channel]) for channel in range(3)) > threshold
        for pixel in pixels
    )
    foreground = [index for index, value in enumerate(mask) if value]
    if not foreground:
        return None

    xs = [index % width for index in foreground]
    ys = [index // width for index in foreground]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    bbox_width = right - left + 1
    bbox_height = bottom - top + 1
    bbox_area = bbox_width * bbox_height
    if bbox_width < 4 or bbox_height < 4:
        return None

    outside = _outside_background(mask, width, height)
    holes = _find_enclosed_regions(
        mask,
        outside,
        width,
        height,
        left,
        top,
        right,
        bottom,
    )

    touches_border = left == 0 or top == 0 or right == width - 1 or bottom == height - 1
    if touches_border or border_deviation > 18:
        confidence = "low"
    elif border_deviation > 7:
        confidence = "medium"
    else:
        confidence = "high"

    return GeometryHints(
        raster_width=width,
        raster_height=height,
        bbox_x=left,
        bbox_y=top,
        bbox_width=bbox_width,
        bbox_height=bbox_height,
        object_aspect_ratio=bbox_width / bbox_height,
        dominant_axis="horizontal" if bbox_width >= bbox_height else "vertical",
        foreground_fill_ratio=len(foreground) / bbox_area,
        enclosed_regions=tuple(holes),
        confidence=confidence,
    )


def _outside_background(mask: bytearray, width: int, height: int) -> bytearray:
    outside = bytearray(width * height)
    queue: deque[int] = deque()
    border_indices = list(range(width)) + list(range((height - 1) * width, height * width))
    border_indices += [row * width for row in range(1, height - 1)]
    border_indices += [row * width + width - 1 for row in range(1, height - 1)]
    for index in border_indices:
        if not mask[index] and not outside[index]:
            outside[index] = 1
            queue.append(index)

    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                neighbor = ny * width + nx
                if not mask[neighbor] and not outside[neighbor]:
                    outside[neighbor] = 1
                    queue.append(neighbor)
    return outside


def _find_enclosed_regions(
    mask: bytearray,
    outside: bytearray,
    width: int,
    height: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> list[HoleHint]:
    seen = bytearray(width * height)
    bbox_area = (right - left + 1) * (bottom - top + 1)
    minimum_area = max(12, int(bbox_area * 0.001))
    regions: list[HoleHint] = []

    for y in range(top + 1, bottom):
        for x in range(left + 1, right):
            start = y * width + x
            if mask[start] or outside[start] or seen[start]:
                continue
            queue = deque([start])
            seen[start] = 1
            points: list[tuple[int, int]] = []
            while queue:
                index = queue.popleft()
                px, py = index % width, index // width
                points.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if left < nx < right and top < ny < bottom:
                        neighbor = ny * width + nx
                        if not mask[neighbor] and not outside[neighbor] and not seen[neighbor]:
                            seen[neighbor] = 1
                            queue.append(neighbor)

            if len(points) < minimum_area or len(points) > bbox_area * 0.25:
                continue
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            region_width = max(xs) - min(xs) + 1
            region_height = max(ys) - min(ys) + 1
            rectangular_fill = len(points) / (region_width * region_height)
            if region_width < 3 or region_height < 3 or rectangular_fill < 0.45:
                continue
            regions.append(
                HoleHint(
                    center_x=((min(xs) + max(xs)) / 2 - left) / (right - left + 1),
                    center_y=((min(ys) + max(ys)) / 2 - top) / (bottom - top + 1),
                    width=region_width / (right - left + 1),
                    height=region_height / (bottom - top + 1),
                    area_fraction=len(points) / bbox_area,
                )
            )

    return sorted(regions, key=lambda region: region.area_fraction, reverse=True)[:8]
