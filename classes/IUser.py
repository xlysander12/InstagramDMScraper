class IUser:
    def __init__(self, id: int, username: str, full_name: str, short_name: str):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.short_name = short_name
