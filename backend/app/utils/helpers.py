from typing import Any, Dict


def to_dict(obj: Any) -> Dict:
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj.__dict__
