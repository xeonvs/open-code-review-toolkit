"""Register bounded, reproducible property-test profiles for the shared suite."""

from hypothesis import settings

settings.register_profile(
    "ocr-ci", max_examples=100, derandomize=True, database=None, deadline=1000, print_blob=False
)
settings.register_profile("ocr-local", parent=settings.get_profile("ocr-ci"), max_examples=1000)
settings.load_profile("ocr-ci")
