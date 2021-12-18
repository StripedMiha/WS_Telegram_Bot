class KeyboardData:

    def __init__(self, text: str, o_id: int, action: str = 'empty'):
        self.text: str = text
        self.id: int = o_id
        self.action: str = action
