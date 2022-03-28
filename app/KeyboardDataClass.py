from typing import Union


class KeyboardData:

    def __init__(self, text: str, o_id: Union[int, str], action: str = 'empty'):
        self.text: str = text
        self.id: int = o_id
        self.action: str = action

    def __repr__(self):
        return f"{self.text}, {self.id}, {self.action}"
