"""Read-only signed 2.04 UI archive index parser."""
from dataclasses import dataclass
import struct
from .dependencies import load_archive_helpers

hashlittle, decrypt = load_archive_helpers()

def checksum(data):
    return hashlittle(data, 0xC5EDE)

class Cursor:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, size):
        if size < 0 or size > len(self.data) - self.pos:
            raise ValueError(f'Truncated section at {self.pos}: needs {size} bytes')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def unpack(self, fmt):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))

    def blob(self):
        return self.take(self.unpack('<I')[0])

    def records(self, fmt, count):
        size = struct.calcsize(fmt)
        return tuple(struct.iter_unpack(fmt, self.take(count * size)))

def trie_strings(data):
    """Resolve compact nodes once, accepting only backward node-boundary links."""
    c, nodes = Cursor(data), {}
    while c.pos < len(data):
        start, back = c.pos, 0
        for shift in range(0, 35, 7):
            value = c.take(1)[0]
            back |= (value & 127) << shift
            if not value & 128:
                break
        else:
            raise ValueError('Overlong trie back-reference')
        suffix = c.take(c.take(1)[0]).decode('utf-8')
        if back and start - back not in nodes:
            raise ValueError('Trie reference does not point to an earlier node')
        nodes[start] = (nodes[start - back] if back else '') + suffix
    return nodes

def safe_asset_path(path):
    parts = path.split('/')
    if not path or '\\' in path or ':' in path or any(p in ('', '.', '..') for p in parts):
        raise ValueError(f'Unsafe asset path: {path!r}')
    return path

@dataclass(frozen=True)
class Entry:
    path: str
    offset: int
    stored: int
    original: int
    chunk: int
    flags: int

@dataclass(frozen=True)
class Pamt:
    metadata: bytes
    chunks: tuple
    dirs: bytes
    names: bytes
    directories: tuple
    files: tuple
    extensions: bytes

    @classmethod
    def parse(cls, data):
        c = Cursor(data)
        expected, count = c.unpack('<II')
        metadata = c.take(4)
        if checksum(data[12:]) != expected:
            raise ValueError('PAMT body checksum mismatch')
        chunks = c.records('<III', count)
        dirs, names = c.blob(), c.blob()
        directories = c.records('<IiII', c.unpack('<I')[0])
        files = c.records('<IIIIHBB', c.unpack('<I')[0])
        extensions = c.blob()
        if c.pos != len(data):
            raise ValueError('Unexpected bytes after PAMT extensions')
        result = cls(metadata, chunks, dirs, names, directories, files, extensions)
        result.entries()
        return result

    def entries(self):
        dirs, names = trie_strings(self.dirs), trie_strings(self.names)
        if not self.extensions.endswith(b'\0'):
            raise ValueError('Unterminated extension table')
        extensions = self.extensions.decode('ascii').split('\0')[:-1]
        chunks = {cid: size for cid, _, size in self.chunks}
        if len(chunks) != len(self.chunks):
            raise ValueError('Duplicate PAZ chunk ID')
        entries, covered, paths = [], set(), set()
        for dhash, doff, first, count in self.directories:
            directory = '' if doff == -1 else dirs[doff]
            if checksum(directory.encode()) != dhash:
                raise ValueError(f'Directory checksum mismatch: {directory!r}')
            if first + count > len(self.files):
                raise ValueError('Directory file range exceeds table')
            for i in range(first, first + count):
                if i in covered:
                    raise ValueError('Overlapping directory file ranges')
                covered.add(i)
                noff, offset, stored, original, cid, flags, ext = self.files[i]
                if cid not in chunks or offset + stored > chunks[cid] or ext >= len(extensions):
                    raise ValueError('Invalid chunk, extent or extension ordinal')
                name = names[noff] + extensions[ext]
                path = safe_asset_path(directory + '/' + name if directory else name)
                if path in paths:
                    raise ValueError('Duplicate asset path')
                paths.add(path)
                entries.append(Entry(path, offset, stored, original, cid, flags))
        if len(covered) != len(self.files):
            raise ValueError('Unclaimed file records')
        return tuple(entries)
