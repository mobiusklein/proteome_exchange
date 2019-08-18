import pprint

DEFAULT_MAX_LEN_DISPLAY = 80

def simple_repr(self):  # pragma: no cover
    '''A convenient function for automatically generating a ``__repr__``-like
    string for arbitrary objects.
    Returns
    -------
    str
    '''
    template = "{self.__class__.__name__}({d})"

    MAX_LEN_DISPLAY = getattr(self, "MAX_LEN_DISPLAY", DEFAULT_MAX_LEN_DISPLAY)

    def formatvalue(v):
        if isinstance(v, float):
            return "%0.4f" % v
        elif isinstance(v, str):
            if len(v) > MAX_LEN_DISPLAY:
                return repr(v[:MAX_LEN_DISPLAY] + '...')
            return repr(v)
        else:
            return pprint.pformat(v)

    if not hasattr(self, "__slots__"):
        d = [
            "%s=%s" % (k, formatvalue(v)) if v is not self else "(...)" for k, v in sorted(
                self.__dict__.items(), key=lambda x: x[0])
            if (not k.startswith("_") and not callable(v)) and not (v is None)]
    else:
        d = [
            "%s=%s" % (k, formatvalue(v)) if v is not self else "(...)" for k, v in sorted(
                [(name, getattr(self, name)) for name in self.__slots__], key=lambda x: x[0])
            if (not k.startswith("_") and not callable(v)) and not (v is None)]

    return template.format(self=self, d=', '.join(d))


class Base(object):
    '''A convenience base class for non-critical code to provide types
    with automatic :meth:`__repr__` methods using :func:`simple_repr`
    '''
    __repr__ = simple_repr


class Bundle(Base):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self[key] = value

    def __getitem__(self, key):
        return self.__dict__[key.replace(" ", "_")]

    def __setitem__(self, key, value):
        self.__dict__[key.replace(" ", "_")] = value