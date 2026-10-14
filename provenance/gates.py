"""Scientific obligations remain active under Python's optimized execution."""
def require(condition, message='scientific obligation failed'):
    if not condition:
        raise ValueError(message)
