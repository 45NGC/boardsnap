"""Find complete photographed 8x8 grids with moderate perspective, without a model."""

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from boardsnap.detection import BoardDetectionError


@dataclass(frozen=True)
class BoardQuadrilateral:
    """TL, TR, BR, BL grid boundaries in original RGB image coordinates.

    Ordering describes the photographed view, not chess orientation. Coordinates
    are floating point boundaries, independent of any piece recognition.
    """

    corners: tuple[tuple[float, float], ...]


def _ordered(points):
    points = np.asarray(points, np.float32).reshape(4, 2)
    center = points.mean(0)
    points = points[np.argsort(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))]
    return np.roll(points, -np.argmin(points.sum(1)), axis=0)


def _valid_quad(points, width, height, minimum=80):
    if not np.isfinite(points).all() or not cv2.isContourConvex(points):
        return False
    if np.any(points < 0) or np.any(points[:, 0] > width) or np.any(points[:, 1] > height):
        return False
    edges = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
    return (edges.min() >= minimum and edges.max() / edges.min() < 2
            and cv2.contourArea(points) >= minimum ** 2)


def _contour_candidates(pixels):
    gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 1)
    candidates = []
    masks = [cv2.Canny(gray, low, high) for low, high in ((25, 75), (60, 150))]
    for channel in cv2.split(pixels):
        smooth = cv2.GaussianBlur(channel, (5, 5), 1)
        _, threshold = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        masks.append(threshold)
    for mask in masks:
        for work in (mask, cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))):
            contours, _ = cv2.findContours(work, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                if cv2.contourArea(contour) < 80 ** 2:
                    continue
                perimeter = cv2.arcLength(contour, True)
                for epsilon in (.01, .02, .035):
                    polygon = cv2.approxPolyDP(contour, epsilon * perimeter, True)
                    if len(polygon) != 4:
                        continue
                    quad = _ordered(polygon)
                    if _valid_quad(quad, pixels.shape[1], pixels.shape[0]):
                        if not any(np.max(np.linalg.norm(quad - old, axis=1)) < 4 for old in candidates):
                            candidates.append(quad)
    return candidates


def _line_candidates(pixels):
    """Propose quadrilaterals from two families of nearly regular grid lines."""
    gray = cv2.GaussianBlur(cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY), (5, 5), 1)
    edges = cv2.Canny(gray, 12, 40)
    segments = cv2.HoughLinesP(edges, 1, np.pi/720, 45,
        minLineLength=max(45, min(gray.shape)*.12), maxLineGap=30)
    if segments is None:
        return []
    families = [[], []]
    for x1, y1, x2, y2 in segments[:, 0].astype(float):
        dx, dy = x2-x1, y2-y1
        length = np.hypot(dx, dy)
        if abs(dx) < abs(dy)*.5:
            a, b, axis = dx/dy, x1-dx/dy*y1, 0
        elif abs(dy) < abs(dx)*.5:
            a, b, axis = dy/dx, y1-dy/dx*x1, 1
        else:
            continue
        center = gray.shape[axis]/2
        families[axis].append((a*center+b, a, b, length))
    pairs = []
    for family in families:
        distinct = []
        for line in sorted(family, key=lambda v: -v[3]):
            if not any(abs(line[0]-old[0]) < 4 for old in distinct):
                distinct.append(line)
        distinct = sorted(distinct[:60])
        positions = np.array([v[0] for v in distinct])
        proposals = []
        for i, first in enumerate(distinct):
            for last in distinct[i+1:]:
                step = (last[0]-first[0])/8
                if step < 12:
                    continue
                # Projective spacing: three lines at ranks 0, 4 and 8 determine
                # t(k)=(a*k+b)/(c*k+1). Equal spacing alone fails under perspective.
                middles = positions[abs(positions-(first[0]+last[0])/2) < step*1.1]
                best = None
                for middle in middles:
                    c = (last[0]+first[0]-2*middle)/(8*(middle-last[0]))
                    if not .5 < 1+8*c < 2:
                        continue
                    a = middle*c+(middle-first[0])/4
                    expected = (a*np.arange(9)+first[0])/(c*np.arange(9)+1)
                    distance = np.min(abs(expected[:, None]-positions), axis=1)/step
                    if np.count_nonzero(distance < .14) >= 8:
                        score = float(distance.sum())
                        best = score if best is None else min(best, score)
                if best is not None:
                    proposals.append((best, first, last))
        pairs.append(sorted(proposals, key=lambda v: v[0])[:12])
    result = []
    for _, left, right in pairs[0]:
        for _, top, bottom in pairs[1]:
            points = []
            for vertical, horizontal in ((left, top), (right, top), (right, bottom), (left, bottom)):
                a, b = vertical[1:3]
                c, d = horizontal[1:3]
                x = (a*d+b)/(1-a*c)
                points.append((x, c*x+d))
            quad = np.float32(points)
            if _valid_quad(quad, pixels.shape[1], pixels.shape[0]):
                result.append(quad)
    return result


def _warp(pixels, corners):
    transform = cv2.getPerspectiveTransform(corners.astype(np.float32),
        np.float32([[0, 0], [512, 0], [512, 512], [0, 512]]))
    return cv2.warpPerspective(pixels, transform, (512, 512)), transform


def _grid_evidence(patch):
    """Check cell corners, fourteen internal lines and four complete outer rims.

    Cell corners avoid the wide piece bases that reach the lower edge of occupied
    squares. This differs from sampling entire rims in the digital detector.
    """
    patch = patch.astype(np.float32)
    offsets = np.r_[5:12, 52:59]
    values = np.empty((8, 8, 3), np.float32)
    for row in range(8):
        for col in range(8):
            values[row, col] = np.median(patch[row*64 + offsets[:, None], col*64 + offsets], axis=(0, 1))
    parity = np.indices((8, 8)).sum(0) % 2
    # Screen photographs can darken strongly toward one side. Estimate each
    # rank's two backgrounds instead of treating illumination as a third color.
    centers = np.array([[np.median(values[r, parity[r] == i], axis=0) for i in (0, 1)] for r in range(8)])
    vectors = centers[:, 0] - centers[:, 1]
    contrast = np.linalg.norm(vectors, axis=1)
    direction = np.median(vectors, axis=0)
    if (contrast.min() < 25 or np.min(vectors @ direction / (contrast * max(1., np.linalg.norm(direction)))) < .8):
        return False
    def matches(samples, expected, ranks):
        own = np.linalg.norm(samples - centers[ranks, expected], axis=-1)
        other = np.linalg.norm(samples - centers[ranks, 1-expected], axis=-1)
        return (own < contrast[ranks]*.65) & (other-own > contrast[ranks]*.2)
    correct = matches(values, parity, np.arange(8)[:, None])
    if correct.sum() < 54 or min(correct.sum(0).min(), correct.sum(1).min()) < 5:
        return False
    for axis, view in enumerate((patch, patch.transpose(1, 0, 2))):
        # All seven boundaries must have sustained evidence, not just a square frame.
        for index in range(1, 8):
            edge = index * 64
            left = np.median(view[:, edge-5:edge-2], axis=1)
            right = np.median(view[:, edge+2:edge+5], axis=1)
            if np.mean(np.linalg.norm(right-left, axis=1) > max(12, float(np.median(contrast))*.2)) < .6:
                return False
        for band, first in ((view[1:4], 0), (view[-4:-1], 1)):
            samples = np.array([np.median(band[:, c*64+offsets].reshape(-1, 3), axis=0) for c in range(8)])
            ranks = np.arange(8) if axis else (0 if first == 0 else 7)
            if matches(samples, (np.arange(8)+first) % 2, ranks).sum() < 6:
                return False
    return True


def _refine(pixels, corners):
    """Fit interior grid intersections; outer contour alone is not geometry."""
    patch, transform = _warp(pixels, corners)
    lines = []
    for axis in (0, 1):
        view = patch if axis == 0 else patch.transpose(1, 0, 2)
        gradient = np.linalg.norm(view[:, 3:].astype(np.float32) - view[:, :-3].astype(np.float32), axis=2)
        axis_lines = []
        for index in range(1, 8):
            target = index * 64
            samples = []
            for y in (np.arange(8)[:, None]*64 + np.array([5, 8, 11, 53, 56, 59])).ravel():
                lo, hi = target - 16, target + 15
                x = lo + int(np.argmax(gradient[y, lo:hi]))
                if gradient[y, x] >= 18:
                    # Center broad derivative peaks instead of choosing their
                    # first pixel; sample beside cell corners to avoid glyphs.
                    a, b = max(lo, x-2), min(hi, x+3)
                    weights = gradient[y, a:b]
                    samples.append((float(np.average(np.arange(a, b), weights=weights)) + 2., y))
            if len(samples) < 30:
                return corners
            vx, vy, x0, y0 = cv2.fitLine(np.float32(samples), cv2.DIST_HUBER, 0, .01, .01).ravel()
            if abs(vy) < .98:
                return corners
            # x = a*y + b, or y = a*x + b for the transposed view.
            axis_lines.append((float(vx / vy), float(x0 - vx / vy * y0)))
        lines.append(axis_lines)
    expected, observed = [], []
    for col, (a, b) in enumerate(lines[0], 1):
        for row, (c, d) in enumerate(lines[1], 1):
            x = (a * d + b) / (1 - a * c)
            y = c * x + d
            expected.append((col * 64, row * 64))
            observed.append((x, y))
    correction, inliers = cv2.findHomography(np.float32(expected), np.float32(observed), cv2.RANSAC, 1.5)
    if correction is None or inliers.sum() < 40:
        return corners
    square = np.float32([[[0, 0], [512, 0], [512, 512], [0, 512]]])
    corrected = cv2.perspectiveTransform(square, correction)[0]
    if np.max(np.linalg.norm(corrected - square[0], axis=1)) > 24:
        return corners
    return cv2.perspectiveTransform(corrected[None], np.linalg.inv(transform))[0]


def _continues(pixels, corners):
    """Reject 8x8 subregions of larger checkerboards, using adjacent visible cells."""
    patch, transform = _warp(pixels, corners)
    colors = np.array([[np.median(patch[r*64+8:r*64+18, c*64+8:c*64+18].reshape(-1, 3), axis=0)
                        for c in range(8)] for r in range(8)])
    parity = np.indices((8, 8)).sum(0) % 2
    centers = np.array([np.median(colors[parity == i], axis=0) for i in (0, 1)])
    contrast = np.linalg.norm(centers[0] - centers[1])
    inverse = np.linalg.inv(transform)
    for axis in (0, 1):
        for edge, first in ((-16, 1), (528, 0)):
            coords = np.float32([[(edge, i*64+12) if axis == 0 else (i*64+12, edge)
                                 for i in range(8)]])
            source = cv2.perspectiveTransform(coords, inverse)[0].round().astype(int)
            valid = ((source[:, 0] >= 0) & (source[:, 0] < pixels.shape[1])
                     & (source[:, 1] >= 0) & (source[:, 1] < pixels.shape[0]))
            if valid.sum() < 6:
                continue
            x, y = source[valid].T
            samples = pixels[y, x].astype(float)
            expected = (np.arange(8)[valid] + first) % 2
            own = np.linalg.norm(samples - centers[expected], axis=1)
            other = np.linalg.norm(samples - centers[1 - expected], axis=1)
            if np.count_nonzero((own < contrast * .5) & (other - own > contrast * .2)) >= 6:
                return True
    return False


def detect_photo_board(image: Image.Image) -> BoardQuadrilateral:
    """Return one fully visible photographed grid, or a structured detection error.

    RGB pixels only. No annotations, source paths, known colors or neural models.
    Conservative moderate-perspective scope; never reconstruct off-image cells.
    The existing digital detector and recognition pipeline are unchanged.
    """
    if not isinstance(image, Image.Image):
        raise TypeError('Expected a Pillow image.')
    if image.mode != 'RGB':
        raise ValueError('Expected RGB pixels; normalize the input first.')
    scale = min(1., 1200 / max(1, *image.size))
    size = (round(image.width * scale), round(image.height * scale))
    if min(size) < 80:
        raise BoardDetectionError('BOARD_NOT_FOUND', 'Image is too small or narrow for a supported photographic grid.')
    work = cv2.resize(np.asarray(image), size, interpolation=cv2.INTER_AREA)
    accepted = []
    for propose in (_contour_candidates, _line_candidates):
        for proposal in propose(work):
            refined = _refine(work, proposal)
            if not _valid_quad(refined, work.shape[1], work.shape[0]):
                continue
            patch, _ = _warp(work, refined)
            if not _grid_evidence(patch):
                continue
            if _continues(work, refined):
                continue
            if not any(np.max(np.linalg.norm(refined - old, axis=1)) < 12 for old in accepted):
                accepted.append(refined)
        if accepted:
            break
    if not accepted:
        raise BoardDetectionError('BOARD_NOT_FOUND', 'No complete supported photographic chessboard was detected.')
    if len(accepted) != 1:
        raise BoardDetectionError('UNSUPPORTED_IMAGE', 'Multiple photographic chessboards were detected.')
    factors = np.array([image.width / work.shape[1], image.height / work.shape[0]])
    corners = accepted[0] * factors
    return BoardQuadrilateral(tuple(tuple(map(float, p)) for p in corners))
