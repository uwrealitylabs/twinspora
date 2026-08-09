"""Minimal KiCad s-expression parser."""


def parse(text):
    """Parse s-expr text into nested lists. Atoms are str; quoted strings are ('str', value)."""
    i, n = 0, len(text)
    stack = []
    cur = None
    while i < n:
        c = text[i]
        if c == '(':
            new = []
            if cur is not None:
                cur.append(new)
                stack.append(cur)
            cur = new
            i += 1
        elif c == ')':
            if stack:
                cur = stack.pop()
            else:
                return cur
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == '\\':
                    buf.append(text[j:j + 2])
                    j += 2
                elif text[j] == '"':
                    break
                else:
                    buf.append(text[j])
                    j += 1
            cur.append(('str', ''.join(buf)))
            i = j + 1
        elif c in ' \t\r\n':
            i += 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()"':
                j += 1
            cur.append(text[i:j])
            i = j
    return cur


def sym(node):
    """First element as a plain symbol string, or None."""
    if isinstance(node, list) and node and isinstance(node[0], str):
        return node[0]
    return None


def val(x):
    """Unwrap a quoted string or return the atom."""
    if isinstance(x, tuple) and x[0] == 'str':
        return x[1]
    return x


def find(node, name):
    """First child list with the given head symbol."""
    for ch in node:
        if isinstance(ch, list) and sym(ch) == name:
            return ch
    return None


def findall(node, name):
    return [ch for ch in node if isinstance(ch, list) and sym(ch) == name]


def nums(node, start=1):
    return [float(x) for x in node[start:] if isinstance(x, str)]
