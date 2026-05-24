from ..config import LABEL_SHADES

class LabelStore:
    def __init__(self):
        self._labels = []   # [{"name":str, "key":str, "shade":str}]

    def add(self, name, key="", shade=None):
        idx   = len(self._labels)
        shade = shade or LABEL_SHADES[idx % len(LABEL_SHADES)]
        self._labels.append({"name": name, "key": key, "shade": shade})

    def remove(self, idx):
        if 0 <= idx < len(self._labels):
            self._labels.pop(idx)

    def get(self, idx):
        return self._labels[idx] if 0 <= idx < len(self._labels) else None

    def by_key(self, key):
        for lb in self._labels:
            if lb["key"] == key:
                return lb
        return None

    def by_name(self, name):
        for lb in self._labels:
            if lb["name"] == name:
                return lb
        return None

    @property
    def labels(self):
        return list(self._labels)

    def to_list(self):
        return list(self._labels)

    def from_list(self, lst):
        self._labels = list(lst)
