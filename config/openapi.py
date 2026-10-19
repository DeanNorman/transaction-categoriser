"""Schema hooks. The brief writes the paths without a trailing slash; the router accepts both; the schema shows the brief's."""


def strip_trailing_slash(endpoints):
    return [(path.rstrip("/") or "/", regex, method, callback) for path, regex, method, callback in endpoints]
