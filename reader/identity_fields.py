"""Predict an editor's ID from their name and a revision's time from its ID."""
from bisect import bisect_left
from datetime import datetime, timedelta


HEADER = b"^WIKIREVISION1\n"
EPOCH = datetime(2000, 1, 1)
USER = (b"        <username>", b"</username>")
USER_ID = (b"        <id>", b"</id>")
REV_ID = (b"      <id>", b"</id>")
STAMP = (b"      <timestamp>", b"</timestamp>")


def value(line, tags):
    prefix, suffix = tags
    if line.startswith(prefix) and line.endswith(suffix):
        return line[len(prefix):-len(suffix)]
    return None


def xml(tags, content):
    return tags[0] + content + tags[1]


def seconds(text):
    try:
        if len(text) == 20 and text[-1:] == b"Z":
            dt = datetime.fromisoformat(text[:-1].decode("ascii"))
            if dt.isoformat(timespec="seconds").encode() == text[:-1]:
                return (dt - EPOCH) // timedelta(seconds=1)
    except (ValueError, OverflowError, UnicodeError, TypeError):
        pass
    return None


class RevisionTimes:
    def __init__(self):
        self.ordered = []
        self.timestamps = {}

    def prediction(self, revision, pos):
        ids, times = self.ordered, self.timestamps
        if revision in times:
            return times[revision]
        if not ids:
            return None
        if pos == 0:
            return times[ids[0]]
        if pos == len(ids):
            return times[ids[-1]]
        left, right = ids[pos-1], ids[pos]
        return times[left] + (revision-left) * (times[right]-times[left]) // (right-left)

    def remember(self, revision, pos, timestamp):
        if revision not in self.timestamps:
            self.ordered.insert(pos, revision)
        self.timestamps[revision] = timestamp


def convert(source, target, encoding):
    users, times = {}, RevisionTimes()
    name = revision = None
    stats = {"editor_ids_copied": 0, "timestamps_predicted": 0}
    with open(source, "rb") as src, open(target, "wb", buffering=1 << 20) as out:
        if encoding:
            out.write(HEADER)
        elif src.readline() != HEADER:
            raise ValueError("invalid revision stream")
        for raw in src:
            # Only these markers and XML indents can affect the predictor.
            if name is None and revision is None and not raw.startswith((b"^", b"      <", b"        <")):
                out.write(raw)
                continue
            newline = raw.endswith(b"\n")
            line = raw[:-1] if newline else raw
            original = line
            encoded = b"^" + line if line.startswith(b"^") else line
            if not encoding and line.startswith(b"^"):
                if line.startswith(b"^^"):
                    original = line[1:]
                elif line == b"^u" and name is not None:
                    original = xml(USER_ID, users[name])
                elif line.startswith(b"^t") and revision is not None:
                    pos = bisect_left(times.ordered, revision)
                    estimate = times.prediction(revision, pos)
                    if estimate is None:
                        raise ValueError("timestamp reference has no history")
                    dt = EPOCH + timedelta(seconds=estimate + int(line[2:]))
                    original = xml(STAMP, dt.isoformat(timespec="seconds").encode() + b"Z")
                else:
                    raise ValueError("unknown revision marker")
            if name is not None:
                ident = value(original, USER_ID)
                if ident is not None:
                    if users.get(name) == ident:
                        encoded = b"^u"
                        stats["editor_ids_copied"] += 1
                    users[name] = ident
            if revision is not None:
                text = value(original, STAMP)
                stamp = seconds(text) if text is not None else None
                if stamp is not None:
                    pos = bisect_left(times.ordered, revision)
                    estimate = times.prediction(revision, pos)
                    if estimate is not None and abs(stamp - estimate) <= 86_400:
                        encoded = b"^t" + str(stamp - estimate).encode()
                        stats["timestamps_predicted"] += 1
                    times.remember(revision, pos, stamp)
            name = value(original, USER)
            ident = value(original, REV_ID)
            revision = int(ident) if ident and len(ident) <= 18 and ident.isdigit() else None
            out.write(encoded if encoding else original)
            if newline:
                out.write(b"\n")
    return stats
