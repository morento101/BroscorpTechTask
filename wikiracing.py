import pprint
import requests
from bs4 import BeautifulSoup, element
from collections import deque


REQUESTS_PER_MINUTE = 100
LINKS_PER_PAGE = 200


class WikiRacer:
    base_wikipedia_url = "https://uk.wikipedia.org"

    def __init__(self):
        self.graph= {}
        self.search_queue = deque()

    def find_path(self, start: str, finish: str) -> list[str]:
        path = [start]

        starting_page = self.base_wikipedia_url + "/wiki/" + start
        starting_page_links = self.get_page_links(starting_page)
        self.graph[start] = starting_page_links
        self.search_queue.extend(starting_page_links)

        pprint.pprint(starting_page_links)
        print(len(starting_page_links))

        return path

    def has_finish_link(self, page_name: str, finish: str) -> bool:
        titles = [link.get("title") for link in self.graph[page_name]]
        return finish in titles
        
    def get_page_links(self, page_url: str) -> set[element.Tag]:
        soup = self.get_soup(page_url)

        body_content = soup.select("div.mw-content-ltr")[0]
        page_links = body_content.find_all("a", class_=lambda cls: cls is None)

        return set(filter(self.validate_link, page_links))

    def get_soup(self, page_url: str) -> BeautifulSoup:
        response = requests.get(page_url)
        return BeautifulSoup(response.text, "html.parser")

    @staticmethod
    def validate_link(link: element.Tag) -> bool:
        if ":" in link.get("title", ""):
            return False

        if not link.get("href", "").startswith("/wiki/"):
            return False 

        if "accesskey" in link.attrs:
            return False

        return True
