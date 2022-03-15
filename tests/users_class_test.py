import datetime
from unittest import TestCase, main, IsolatedAsyncioTestCase

import sqlalchemy.exc

from app.db.structure_of_db import User, Status
from app.exceptions import EmptyCost, FutureDate, WrongDate
from app.tgbot.main import change_date


class UserTest(TestCase):

    def test_get_user(self):
        self.assertEqual(User.get_user(300617281).first_name, "Mikhail")

    def test_get_wrong_user(self):
        with self.assertRaises(ValueError) as e:
            User.get_user(1234)
        self.assertEqual("not enough values to unpack (expected 2, got 0)", e.exception.args[0])

    def test_get_admin_status(self):
        status = Status.get_status("admin")
        self.assertIn(status, User.get_user(300617281).get_status())

    def test_get_black_status(self):
        status = Status.get_status("black")
        self.assertIn(status, User.get_user(582760668).get_status())

    def test_get_user_status(self):
        status = Status.get_status("user")
        self.assertIn(status, User.get_user(833477860).get_status())

    def test_admin_is_admin(self):
        self.assertEqual(User.get_user(300617281).is_admin(), True)

    def test_user_is_admin(self):
        self.assertEqual(User.get_user(833477860).is_admin(), False)

    def test_black_is_admin(self):
        self.assertEqual(User.get_user(582760668).is_admin(), False)

    def test_admin_has_access(self):
        self.assertEqual(User.get_user(300617281).has_access(), True)

    def test_user_has_access(self):
        self.assertEqual(User.get_user(833477860).has_access(), True)

    def test_black_has_access(self):
        self.assertEqual(User.get_user(582760668).has_access(), False)

    def test_admin_blocked(self):
        self.assertEqual(User.get_user(300617281).blocked(), False)

    def test_user_blocked(self):
        self.assertEqual(User.get_user(833477860).blocked(), False)

    def test_black_blocked(self):
        self.assertEqual(User.get_user(582760668).blocked(), True)

    def test_full_name(self):
        self.assertEqual(User.get_user(300617281).full_name(), "Mikhail Ignatenko")

    def test_get_email(self):
        self.assertEqual(User.get_user(300617281).get_email(), "m.ignatenko@smde.ru")

    def test_get_today_date(self):
        self.assertEqual(User.get_user(582760668).get_date(), "today")

    def test_get_custom_date(self):
        self.assertEqual(User.get_user(432113264).get_date(), "11.02.2022")


class UserChangeDateTest(IsolatedAsyncioTestCase):

    async def test_change_date_today(self):
        user = User.get_user(226449626)
        await change_date(user, 'today')
        self.assertEqual(user.get_date(), 'today')

    async def test_change_date_yesterday(self):
        user = User.get_user(226449626)
        await change_date(user, 'yesterday')
        yesterday_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        self.assertEqual(user.get_date(), yesterday_date)

    async def test_change_date_custom(self):
        user = User.get_user(226449626)
        await change_date(user, '10.02.2022')
        self.assertEqual(user.get_date(), '10.02.2022')

    async def test_change_date_future(self):
        user = User.get_user(226449626)
        with self.assertRaises(FutureDate):
            future_date = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%d.%m.%Y")
            await change_date(user, future_date)

    async def test_change_date_wrong(self):
        user = User.get_user(226449626)
        with self.assertRaises(WrongDate):
            await change_date(user, '1002.2022')

    async def test_change_date_wrong2(self):
        user = User.get_user(226449626)
        with self.assertRaises(WrongDate):
            await change_date(user, '40.02.2022')

    async def test_change_date_wrong3(self):
        user = User.get_user(226449626)
        with self.assertRaises(WrongDate):
            await change_date(user, '10.22.2022')

    async def test_change_date_wrong4(self):
        user = User.get_user(226449626)
        with self.assertRaises(WrongDate):
            await change_date(user, '10.02.1022')

    async def test_change_date_wrong5(self):
        user = User.get_user(226449626)
        with self.assertRaises(WrongDate):
            await change_date(user, '40022022')

    async def test_change_date_wrong6(self):
        user = User.get_user(226449626)
        with self.assertRaises(WrongDate):
            await change_date(user, '10..02..2022')


if __name__ == '__main__':
    main()
