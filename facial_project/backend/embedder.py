"""Embedding extraction wrapper.

Tries to use InsightFace if available. If not, provides a deterministic fallback embedding generated
from the image contents so the pipeline can be tested without model downloads.
"""
from typing import List, Optional, Tuple
import numpy as np
import cv2
import os

_HAS_INSIGHT = False
_insight_model = None
# Allow forcing the fallback (useful in low-memory / CI environments)
_DISABLE_INSIGHT = os.environ.get('DISABLE_INSIGHTFACE', '')
if _DISABLE_INSIGHT.lower() in ('1', 'true', 'yes'):
    _HAS_INSIGHT = False
else:
    try:
        import insightface
        from insightface.app import FaceAnalysis
        _HAS_INSIGHT = True
    except Exception:
        _HAS_INSIGHT = False


def load_insightface():
    global _insight_model
    if not _HAS_INSIGHT:
        return None
    if _insight_model is None:
        # use default config; model download may be required
        app = FaceAnalysis(allowed_modules=['detection', 'recognition'])
        # Choose device only if provider exists. Prefer GPU (ctx_id=0) when CUDAExecutionProvider
        # is available in onnxruntime; otherwise use CPU (ctx_id=-1). This avoids onnxruntime
        # warnings on CPU-only machines when an unavailable provider is requested.
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            if 'CUDAExecutionProvider' in providers:
                ctx = 0
            else:
                ctx = -1
        except Exception:
            # if onnxruntime isn't importable or check fails, fall back to CPU
            ctx = -1

        app.prepare(ctx_id=ctx, det_size=(640, 640))
        _insight_model = app
    return _insight_model


def _fallback_embedding_from_image(path: str, dim: int = 512) -> List[float]:
    # Deterministic embedding fallback: resize grayscale, compute ORB descriptors, and hash
    img = cv2.imread(path)
    if img is None:
        # return zero vector on failure
        return [0.0] * dim
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Resize to stable size
    small = cv2.resize(gray, (128, 128))
    orb = cv2.ORB_create(256)
    kps, des = orb.detectAndCompute(small, None)
    if des is None:
        # no keypoints -> deterministic pseudo-random by file bytes
        b = open(path, 'rb').read()
        seed = sum(b) % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.randn(dim)
    else:
        # aggregate descriptors into fixed-dim vector
        flat = des.flatten().astype(np.float32)
        # pad or trim
        if flat.size < dim:
            pad = np.zeros(dim - flat.size, dtype=np.float32)
            arr = np.concatenate([flat, pad])
        else:
            arr = flat[:dim]
        vec = arr
    # normalize
    vec = vec.astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm == 0:
        return [0.0] * dim
    vec = vec / norm
    return vec.tolist()


def _compute_face_ratios(landmarks: np.ndarray) -> dict:
    """
    Compute a few key face ratios from landmarks.
    landmarks: np.ndarray of shape (N, 2)
    Returns a dict of ratios (all values are floats).
    """
    # Example: eye distance, nose width, mouth width, face height
    # These indices are based on common landmark order (InsightFace uses 5 or 68 points)
    ratios = {}
    try:
        if landmarks.shape[0] >= 5:
            # 5-point: [left_eye, right_eye, nose, left_mouth, right_mouth]
            left_eye = landmarks[0]
            right_eye = landmarks[1]
            nose = landmarks[2]
            left_mouth = landmarks[3]
            right_mouth = landmarks[4]
            eye_dist = np.linalg.norm(left_eye - right_eye)
            mouth_width = np.linalg.norm(left_mouth - right_mouth)
            eye_nose = np.linalg.norm(((left_eye + right_eye) / 2) - nose)
            nose_mouth = np.linalg.norm(nose - ((left_mouth + right_mouth) / 2))
            ratios = {
                'eye_dist': float(eye_dist),
                'mouth_width': float(mouth_width),
                'eye_nose': float(eye_nose),
                'nose_mouth': float(nose_mouth),
                'eye_to_mouth_ratio': float(eye_dist / mouth_width) if mouth_width > 0 else 0.0,
                'eye_to_nose_ratio': float(eye_dist / eye_nose) if eye_nose > 0 else 0.0,
            }
        # For 68-point, you can add more ratios if needed
    except Exception:
        pass
    return ratios

def extract_embeddings(image_path: str) -> List[Tuple[List[float], Tuple[int,int,int,int], dict]]:
    """
    Return list of tuples (embedding_vector, bbox, face_ratios) for faces found in image.
    If no InsightFace is available, returns single fallback embedding, bbox covering image, and empty ratios.
    """
    if _HAS_INSIGHT:
        app = load_insightface()
        if app is not None:
            img = cv2.imread(image_path)
            if img is None:
                return []
            faces = app.get(img)
            results = []
            for f in faces:
                emb = f.embedding.tolist()
                bbox = (int(f.bbox[0]), int(f.bbox[1]), int(f.bbox[2]), int(f.bbox[3]))
                # Try to get landmarks and compute ratios
                ratios = {}
                if hasattr(f, 'kps') and f.kps is not None:
                    # f.kps is (N,2) ndarray
                    ratios = _compute_face_ratios(np.array(f.kps))
                results.append((emb, bbox, ratios))
            if len(results) == 0:
                emb = _fallback_embedding_from_image(image_path)
                h, w = img.shape[:2]
                bbox = (0, 0, w, h)
                return [(emb, bbox, {})]
            return results

    # Fallback path
    emb = _fallback_embedding_from_image(image_path)
    img = cv2.imread(image_path)
    if img is None:
        return []
    h, w = img.shape[:2]
    bbox = (0, 0, w, h)
    return [(emb, bbox, {})]
