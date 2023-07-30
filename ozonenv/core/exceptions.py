import typing


class SessionException(Exception):
    def __init__(
        self,
        detail: typing.Optional[str] = None,
    ) -> None:
        if detail is None:
            detail = "Session Expired or Unactive"
        self.detail = detail

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(detail={self.detail!r})"
