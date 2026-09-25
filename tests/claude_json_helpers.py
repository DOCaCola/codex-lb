from pydantic import JsonValue


def array(value: JsonValue) -> list[JsonValue]:
    assert isinstance(value, list)
    return value


def at(value: JsonValue, *path: str | int) -> JsonValue:
    for key in path:
        if isinstance(key, str):
            assert isinstance(value, dict)
            value = value[key]
        else:
            assert isinstance(value, list)
            value = value[key]
    return value
