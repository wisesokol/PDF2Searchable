#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight, robust OCR utility wrapper for PaddleOCR used by the processing script.
Provides TechnicalOCRProcessor.process_page_ocr(image, ocr_engine) which returns a list
of normalized entries: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]], [text, score]]
"""
import typing as _t
import numpy as np
import cv2


class TechnicalOCRProcessor:
    """Simple, robust processor that normalizes PaddleOCR outputs.

    process_page_ocr tries raw OCR first (no preprocessing), then a lightly
    preprocessed image if the raw call returns nothing. The returned format is
    a list of [bbox, [text, score]] where bbox is [[x1,y1],[x2,y1],[x2,y2],[x1,y2]].
    """

    def __init__(self, min_confidence: float = 0.3):
        self.min_confidence = float(min_confidence)

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        # Basic grayscale + CLAHE + denoise + Otsu thresholding
        if image is None:
            return image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.medianBlur(enhanced, 3)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _normalize_bbox(self, bbox) -> _t.Optional[_t.List[_t.List[float]]]:
        if bbox is None:
            return None
        # accept numpy arrays returned by PaddleOCR
        try:
            import numpy as _np
            if isinstance(bbox, _np.ndarray):
                bbox = bbox.tolist()
        except Exception:
            pass
        try:
            # Paddle standard: list of 4 points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4 and all(
                isinstance(pt, (list, tuple)) and len(pt) >= 2 for pt in bbox
            ):
                pts = [[float(pt[0]), float(pt[1])] for pt in bbox]
                # convert to canonical ordering: [top-left, top-right, bottom-right, bottom-left]
                return pts

            # flat 8 values [x1,y1,x2,y2,x3,y3,x4,y4]
            if isinstance(bbox, (list, tuple)) and len(bbox) == 8 and all(
                isinstance(x, (int, float)) for x in bbox
            ):
                f = [float(x) for x in bbox]
                return [[f[0], f[1]], [f[2], f[3]], [f[4], f[5]], [f[6], f[7]]]

            # bbox as [xmin,ymin,xmax,ymax]
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4 and all(
                isinstance(x, (int, float)) for x in bbox
            ):
                xmin, ymin, xmax, ymax = bbox
                return [[float(xmin), float(ymin)], [float(xmax), float(ymin)], [float(xmax), float(ymax)], [float(xmin), float(ymax)]]

        except Exception:
            return None
        return None

    def _parse_paddle_output(self, raw) -> _t.List[_t.Tuple[_t.List[_t.List[float]], str, float]]:
        """Accept several PaddleOCR output shapes and yield tuples (bbox, text, score).

        Known formats:
        - list of [poly, (text, score)] (older Paddle)
        - list of dicts with keys 'rec_texts', 'rec_scores', 'rec_polys'
        - dict with 'rec_texts', 'rec_scores', 'rec_polys'
        """
        parsed = []
        if not raw:
            return parsed

        # dict-like page result
        if isinstance(raw, dict):
            texts = raw.get('rec_texts') or raw.get('dt_boxes_texts') or []
            scores = raw.get('rec_scores') or []
            polys = raw.get('rec_polys') or raw.get('rec_boxes') or raw.get('dt_polys') or []
            for i, t in enumerate(texts):
                text = str(t) if t is not None else ''
                score = float(scores[i]) if i < len(scores) else 1.0
                poly = polys[i] if i < len(polys) else None
                parsed.append((poly, text, score))
            return parsed

        # list - either list of dicts or list of lines
        if isinstance(raw, list):
            # list of page-dicts
            if len(raw) > 0 and isinstance(raw[0], dict) and ('rec_texts' in raw[0] or 'dt_polys' in raw[0]):
                item = raw[0]
                texts = item.get('rec_texts') or item.get('dt_boxes_texts') or []
                scores = item.get('rec_scores') or []
                polys = item.get('rec_polys') or item.get('rec_boxes') or item.get('dt_polys') or []
                for i, t in enumerate(texts):
                    text = str(t) if t is not None else ''
                    score = float(scores[i]) if i < len(scores) else 1.0
                    poly = polys[i] if i < len(polys) else None
                    parsed.append((poly, text, score))
                return parsed

            # list of lines: [[x1,y1],...], (text, score)
            for line in raw:
                try:
                    if not line:
                        continue
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        poly = line[0]
                        text_info = line[1]
                        text = ''
                        score = 1.0
                        # text_info may be (text, score) or just text
                        if isinstance(text_info, (list, tuple)):
                            if len(text_info) >= 1:
                                text = str(text_info[0])
                            if len(text_info) >= 2:
                                try:
                                    score = float(text_info[1])
                                except Exception:
                                    score = 1.0
                        else:
                            text = str(text_info)
                        parsed.append((poly, text, score))
                except Exception:
                    continue
            return parsed

        return parsed

    def process_page_ocr(self, image: np.ndarray, ocr_engine) -> _t.List[_t.List[_t.Any]]:
        """Run OCR and return normalized results suitable for PDF insertion.

        Returns: list of [bbox, [text, score]] where bbox is normalized 4-pt list.
        """
        results = []

        # try raw image first
        raw = []
        try:
            raw = ocr_engine.ocr(image)
        except Exception:
            raw = []

        # if nothing found, try preprocessed
        if not raw:
            try:
                prep = self._preprocess(image)
                raw = ocr_engine.ocr(prep)
            except Exception:
                raw = []

        parsed = self._parse_paddle_output(raw)

        for poly, text, score in parsed:
            if not text:
                continue
            norm = self._normalize_bbox(poly)
            if norm is None:
                continue
            # basic cleaning
            txt = ' '.join(str(text).split()).strip()
            if not txt:
                continue
            if score is None:
                try:
                    score = 1.0
                except Exception:
                    score = 1.0
            try:
                fscore = float(score)
            except Exception:
                fscore = 1.0
            if fscore < self.min_confidence:
                # skip low-confidence by default
                continue
            results.append([norm, [txt, fscore]])

        return results
