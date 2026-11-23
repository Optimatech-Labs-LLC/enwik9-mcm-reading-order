"""Reversible in-order predictions using the current page title and wiki link target."""

import argparse
import lzma
import re
import sys


TITLE = re.compile(rb"^    <title>([^\r\n\x00\xff]{6,512})</title>\r?\n?$")
LINK = re.compile(rb"\[\[([^\[\]|\r\n\x00]{3,512})\|([^\[\]|\r\n\x00]{4,512})\]\]")
PATCH = re.compile(rb"\[\[([^\[\]|\r\n\x00]{3,512})\|\x00([pse])([^\[\]|\r\n\x00]{0,520})\]\]")
RESERVED = re.compile(rb"[\x03\x05\x06\x07\x0c\x1b]")
COMPACT = re.compile(rb"\x1b([\x03\x05\x06\x07\x0c\x1b])|[\x03\x05\x06\x07\x0c]")
SHORT = {b"\x00T": b"\x03", b"\x00t": b"\x05", b"\x00p": b"\x06",
         b"\x00s": b"\x07", b"\x00e": b"\x0c"}
LONG = {v:k for k,v in SHORT.items()}


def compact(line):
    line = RESERVED.sub(lambda m:b"\x1b"+m[0],line)
    if b"\x00" in line:
        for pair, single in SHORT.items():
            line = line.replace(pair,single)
    return line


def expand(line):
    return COMPACT.sub(lambda m:m[1] if m[1] is not None else LONG[m[0]],line)


def number(n):
    return bytes((128+n,)) if n < 64 else bytes((192 + n//64, 128 + n%64))


def take(data):
    if not data or data[0] < 128:
        raise ValueError("missing echo length")
    if data[0] < 192:
        return data[0]-128, data[1:]
    if len(data) < 2 or not (128 <= data[1] < 192):
        raise ValueError("invalid echo length")
    return 64*(data[0]-192) + data[1]-128, data[2:]


def code_link(match):
    target, shown = match.groups()
    limit = min(len(target), len(shown))
    p = 0
    while p < limit and target[p] == shown[p]:
        p += 1
    s = 0
    while s < limit and target[-1-s] == shown[-1-s]:
        s += 1
    choices = [shown]
    if p >= 4:
        choices.append(b"\x00p" + number(p) + shown[p:])
    if s >= 4:
        choices.append(b"\x00s" + number(s) + shown[:len(shown)-s])
    offset = target.find(shown)
    if offset >= 0:
        choices.append(b"\x00e"+number(offset)+number(len(shown)))
    best = min(choices,key=len)
    return b"[["+target+b"|"+best+b"]]" if best != shown else match.group()


def restore_link(match):
    target, mode, data = match.groups()
    n, tail = take(data)
    if n > len(target):
        raise ValueError("echo exceeds link target")
    if mode == b"p":
        shown = target[:n]+tail
    elif mode == b"s":
        shown = tail+target[len(target)-n:]
    else:
        size, remainder = take(tail)
        if remainder or size+n > len(target):
            raise ValueError("invalid embedded label")
        shown = target[n:n+size]
    return b"[["+target+b"|"+shown+b"]]"


def transform(source, dest, packing, mode):
    if packing:
        dest.write(b"WKE1" + mode + b"\n")
    else:
        header = source.readline(7)
        if header not in (b"WKE1T\n", b"WKE1L\n", b"WKE1B\n", b"WKE1S\n"):
            raise ValueError("unknown Wikipedia echo stream")
        mode = header[4:5]
    use_title = mode in (b"T", b"B", b"S")
    use_links = mode in (b"L", b"B", b"S")
    title = lower = b""
    for line in source:
        if mode == b"S" and not packing:
            line = expand(line)
        if line.startswith(b"    <title>"):
            original = line if packing else line.replace(b"\x00\xff",b"\x00")
            declaration = TITLE.fullmatch(original)
            title = declaration[1] if declaration and use_title else b""
            lower = title[:1].lower() + title[1:] if title[:1].isupper() else b""
            if packing:
                quoted = line.replace(b"\x00",b"\x00\xff")
                dest.write(compact(quoted) if mode==b"S" else quoted)
            else:
                dest.write(original)
            continue
        if line.startswith((b"  <page>", b"  </page>")):
            title = lower = b""
        if packing:
            line = line.replace(b"\x00", b"\x00\xff")
            if title:
                line = line.replace(title, b"\x00T")
                if lower:
                    line = line.replace(lower, b"\x00t")
            if use_links and b"[[" in line and b"|" in line:
                line = LINK.sub(code_link,line)
        else:
            if use_links and b"|\x00" in line:
                line = PATCH.sub(restore_link,line)
            if title:
                line = line.replace(b"\x00T",title)
                if lower:
                    line = line.replace(b"\x00t",lower)
            line = line.replace(b"\x00\xff", b"\x00")
        dest.write(compact(line) if mode==b"S" and packing else line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pack", "unpack", "restore"))
    parser.add_argument("input")
    parser.add_argument("--mode",choices=("T","L","B","S"),default="B")
    args = parser.parse_args()
    opener = lzma.open if args.action == "restore" else open
    with opener(args.input,"rb") as src:
        transform(src, sys.stdout.buffer, args.action=="pack",args.mode.encode())
