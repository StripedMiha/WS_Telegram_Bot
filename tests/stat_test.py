from datetime import datetime
from unittest import TestCase, main
from app.tgbot.main import get_work_date_for_report


class ReportTest(TestCase):

    def test_monday(self):
        self.assertEqual(get_work_date_for_report("19:00"), datetime.now().strftime("%Y-%m-%d"))


if __name__ == '__main__':
    main()
