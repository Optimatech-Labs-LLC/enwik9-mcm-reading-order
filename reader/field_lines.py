"""Apply the revision predictor and the earlier title/link predictor in sequence."""
from pathlib import Path
from tempfile import TemporaryDirectory
from identity_fields import convert as revision_fields
from wiki_echo import transform as page_echo


def convert(source, target, encoding):
    with TemporaryDirectory(dir=Path(target).parent) as tmp:
        middle = Path(tmp) / "revisions"
        if encoding:
            stats = revision_fields(source, middle, True)
            with middle.open("rb") as src, open(target, "wb") as dst:
                page_echo(src, dst, True, b"S")
            return stats
        with open(source, "rb") as src, middle.open("wb") as dst:
            page_echo(src, dst, False, b"S")
        return revision_fields(middle, target, False)
