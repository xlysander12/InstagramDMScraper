from enum import Enum


class IMediaType(Enum):
    UNKNOWN = 0
    PHOTO = 1
    VIDEO = 2

    def print(self):
        match self:
            case IMediaType.PHOTO:
                return "Photo"
            case IMediaType.VIDEO:
                return "Video"
            case IMediaType.UNKNOWN:
                return "Media"

    @classmethod
    def from_string(cls, string: str):
        match string:
            case "PHOTO":
                return cls.PHOTO
            case "VIDEO":
                return cls.VIDEO
            case _:
                return cls.UNKNOWN

    @classmethod
    def from_number(cls, number: int):
        match number:
            case 1:
                return cls.PHOTO
            case 2:
                return cls.VIDEO
            case _:
                return cls.UNKNOWN
