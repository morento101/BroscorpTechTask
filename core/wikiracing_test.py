import unittest

import database
import exceptions
import wikiracing
from sqlalchemy import or_


class WikiRacerTest(unittest.TestCase):
    """Tests for WikiRacer.find_path method."""

    racer = wikiracing.WikiRacer()

    def test_1(self):
        path = self.racer.find_path('Дружба', 'Рим')
        self.assertEqual(path, ['Дружба', 'Якопо Понтормо', 'Рим'])

        wikiracing.__dict__["SEARCH_DEPTH"] = 1
        path = self.racer.find_path('Дружба', 'Рим')
        self.assertEqual(path, [])
        wikiracing.__dict__["SEARCH_DEPTH"] = 3

    def test_2(self):
        path = self.racer.find_path('Мітохондріальна ДНК', 'Вітамін K')
        self.assertEqual(
            path,
            [
                'Мітохондріальна ДНК', 'Дезоксирибонуклеїнова кислота',
                'Аденозинтрифосфат', 'Вітамін K'
            ]
        )

    def test_3(self):
        path = self.racer.find_path(
            'Марка (грошова одиниця)', 'Китайський календар'
        )
        self.assertEqual(
            path, ['Марка (грошова одиниця)', '2017', 'Китайський календар']
        )

    def test_4(self):
        path = self.racer.find_path('Фестиваль', 'Пілястра')
        self.assertEqual(path, ['Фестиваль', 'Бароко', 'Пілястра'])

    def test_5(self):
        path = self.racer.find_path('Дружина (військо)', '6 жовтня')
        self.assertEqual(
            path, ['Дружина (військо)', 'Олег', '3 жовтня', '6 жовтня']
        )

        wikiracing.__dict__["SEARCH_DEPTH"] = 2
        path = self.racer.find_path('Дружина (військо)', '6 жовтня')
        self.assertEqual(path, [])
        wikiracing.__dict__["SEARCH_DEPTH"] = 3

    def test_wrong_start(self):
        """Test if ResourceAccessException is raised with wrong start given"""
        with self.assertRaises(exceptions.ResourceAccessException):
            self.racer.find_path('Wrong Article Title', 'No Finish')

    def test_wrong_finish(self):
        """Test if ResourceAccessException is raised with wrong finish given"""
        with self.assertRaises(exceptions.ResourceAccessException):
            self.racer.find_path('Дружба', 'No Finish')


class WikiRacerFunctionsTest(unittest.TestCase):
    """Tests for other methods in WikiRacer class."""

    racer = wikiracing.WikiRacer()

    def test_validate_link(self):
        """Tests link validation.

        Uses fake_a_tag variable to replace bs4.element.Tag object.
        """
        fake_a_tag = {"href": "/wiki/Україна"}
        is_valid = self.racer.validate_link(fake_a_tag)
        self.assertTrue(is_valid)

        fake_a_tag = {"href": "/wiki/Обговорення:Україна"}
        is_valid = self.racer.validate_link(fake_a_tag)
        self.assertFalse(is_valid)

    def test_visit_page(self):
        """Valdates that racer can't visit same link more than ones."""
        page_url = self.racer.base_wikipedia_url + "/wiki/Україна"
        self.racer.visit_page(page_url)

        with self.assertRaises(exceptions.AlreadyVisitedException):
            print(self.racer.visit_page(page_url))


class DatabaseTest(unittest.TestCase):
    """Tests for database module."""

    @classmethod
    def setUpClass(cls):
        """Prepare test class."""
        cls.session, cls.engine = database.connect_to_db(
            "postgres", "postgres", "localhost", 5432, "wiki"
        )

        cls.page1 = database.Page(title="Test1")
        cls.page2 = database.Page(title="Test2", right_pages=[cls.page1])
        cls.session.add_all((cls.page1, cls.page2))

        cls.session.commit()

    def test_page_in_db(self):
        """Validates that page with such exists in db."""
        in_db = database.page_in_db(
            DatabaseTest.session, DatabaseTest.page1.title
        )
        self.assertEqual(in_db, self.page1)

        not_in_db = database.page_in_db(DatabaseTest.session, "Does not exist")
        self.assertIsNone(not_in_db)

    def test_cached_page_db(self):
        """Tests if page with all links is saved in database."""
        is_cached = database.cached_page_db(
            DatabaseTest.session, DatabaseTest.page2.title
        )
        self.assertEqual(is_cached, DatabaseTest.page2)

        is_not_cached = database.cached_page_db(
            DatabaseTest.session, DatabaseTest.page1.title
        )
        self.assertIsNone(is_not_cached)

    def test_save_page_with_links(self):
        """Test saving page with its links."""
        self.assertFalse(DatabaseTest.page1.right_pages.all())

        links_titles = ["T-72", "Leopard 2"]
        page = database.save_page_with_links(
            DatabaseTest.session, "Test1", links_titles
        )

        self.assertTrue(page.right_pages.all())
        self.assertEqual(
            DatabaseTest.page1.right_pages.all(), page.right_pages.all()
        )

    def test_has_finish_link(self):
        """Checks if page has finish link."""
        links_titles = ["T-72", "Leopard 2"]
        page = database.save_page_with_links(
            DatabaseTest.session, "Test1", links_titles
        )

        for title in links_titles:
            with self.subTest():
                has_finish = database.has_finish_link(
                    DatabaseTest.session, page, title
                )
                self.assertTrue(has_finish)

        has_finish = database.has_finish_link(
            DatabaseTest.session, page, "No title"
        )
        self.assertFalse(has_finish)

    def test_get_page_links(self):
        """Extract all links from page."""
        links_titles = ["T-72", "Leopard 2"]
        page = database.save_page_with_links(
            DatabaseTest.session, "Test1", links_titles
        )

        links_titles_from_func = database.get_page_links(page)
        self.assertEqual(links_titles, links_titles_from_func)

    def tearDown(self):
        """Cleanup after each test."""
        children_pages = self.session.query(database.Page).filter(
            or_(
                database.Page.title == "T-72",
                database.Page.title == "Leopard 2"
            )
        ).all()
        for child in children_pages:
            self.session.delete(child)

    @classmethod
    def tearDownClass(cls):
        """Cleanup the test class."""
        cls.session.delete(cls.page1)
        cls.session.delete(cls.page2)
        cls.session.commit()


if __name__ == '__main__':
    unittest.main()
