from enum import Enum


def get_enum_value(enum_cls: type[Enum]) -> list[str]:
    return [e.value for e in enum_cls]