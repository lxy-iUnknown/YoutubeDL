class __Default:
    def __bool__(self):
        return False

    def __repr__(self):
        return '<DEFAULT>'


DEFAULT = __Default()
