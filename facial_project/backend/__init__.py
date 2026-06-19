"""Backend package for facial forensics prototype.

This module also configures a small warning filter to suppress a noisy onnxruntime
UserWarning that appears when CUDAExecutionProvider is requested but not available
on CPU-only machines. The warnings are cosmetic and tests still exercise CPU path.
"""
import warnings

# Suppress a noisy onnxruntime provider-not-available warning (regex)
warnings.filterwarnings(
	"ignore",
	message=r".*CUDAExecutionProvider.*not in available provider names.*",
	category=UserWarning,
)

