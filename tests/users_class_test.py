from unittest import TestCase, main

import sqlalchemy.exc

from app.db.structure_of_db import User


class UserTest(TestCase):

    def test_get_user(self):
        self.assertEqual(User.get_user(300617281).first_name, "Mikhail")

    def test_get_wrong_user(self):
        with self.assertRaises(ValueError) as e:
            User.get_user(1234)
        self.assertEqual("not enough values to unpack (expected 2, got 0)", e.exception.args[0])

    def test_get_admin_status(self):
        self.assertEqual(User.get_user(300617281).get_status(), "admin")

    def test_get_black_status(self):
        self.assertEqual(User.get_user(582760668).get_status(), "black")

    def test_get_user_status(self):
        self.assertEqual(User.get_user(833477860).get_status(), "user")

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


if __name__ == '__main__':
    main()
