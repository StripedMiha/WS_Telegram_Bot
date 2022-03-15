class EmptyCost(ValueError):
    pass


class WrongTime(ValueError):
    pass


class WrongDate(ValueError):
    pass


class FutureDate(WrongDate):
    pass


class EmptyDayCosts(ValueError):
    pass


class NotUserTime(WrongTime):
    pass


class NoRemindNotification(ValueError):
    pass


class CancelInput(Exception):
    pass
