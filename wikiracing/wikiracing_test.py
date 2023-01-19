import unittest

from wikiracing.wikiracing import WikiRacer


class WikiRacerTest(unittest.TestCase):

    racer = WikiRacer()

    def test_1(self):
        path = self.racer.find_path('Дружба', 'Рим')
        self.assertEqual(path, ['Дружба', 'Якопо Понтормо', 'Рим'])

    # def test_2(self):
    #     path = self.racer.find_path('Мітохондріальна ДНК', 'Вітамін K')
    #     print(path)

    # def test_3(self):
    #     path = self.racer.find_path(
    #         'Марка (грошова одиниця)', 'Китайський календар'
    #     )
    #     print(path)

    # def test_4(self):
    #     path = self.racer.find_path('Фестиваль', 'Пілястра')
    #     print(path)

    # def test_5(self):
    #     path = self.racer.find_path('Дружина (військо)', '6 жовтня')
    #     print(path)


if __name__ == '__main__':
    unittest.main()
