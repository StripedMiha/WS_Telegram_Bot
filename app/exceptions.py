class EmptyCost(ValueError):
    pass


class WrongTime(ValueError):
    pass


class WrongDate(ValueError):
    pass


class FutureDate(WrongDate):
    pass
