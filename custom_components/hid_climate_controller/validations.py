class ValidationException(Exception):
    def __init__(self, reason="") -> None:
        super().__init__(reason)
        self.reason = reason
