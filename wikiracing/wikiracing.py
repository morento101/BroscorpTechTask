import logging
import queue
import re
import time

import requests
from bs4 import BeautifulSoup, element

from wikiracing.database import connect_to_db
from wikiracing.exceptions import (AlreadyVisitedException,
                                   ResourceAccessException)

REQUESTS_PER_MINUTE = 100
LINKS_PER_PAGE = 200
SEARCH_DEPTH = 3


class WikiRacer:
    base_wikipedia_url = "https://uk.wikipedia.org"

    def __init__(self, depth=0):
        self.depth = depth
        self.graph = None
        self.path = None
        self.visited_pages = None
        self.exceptions = None

        self.session, self.engine = connect_to_db(
            "postgres", "postgres", "localhost", 5432, "wiki"
        )

    def find_path(self, start: str, finish: str) -> list[str]:
        if self.depth > SEARCH_DEPTH:
            return

        if start == finish:
            return [start]

        self.graph = {}
        self.path = []
        self.search_queue = queue.Queue()
        self.visited_pages = set()
        self.exceptions = queue.Queue()

        self.search_queue.put(start)

        while not self.search_queue.empty():
            try:
                current_page = self.search_queue.get()
                page_url = self.base_wikipedia_url + "/wiki/" + current_page

                try:
                    page_links = self.get_page_links(page_url)
                except AlreadyVisitedException:
                    continue

                self.graph[current_page] = page_links

                if self.has_finish_link(current_page, finish):
                    racer = WikiRacer(depth=self.depth+1)
                    result = racer.find_path(start, finish=current_page)

                    if result is None or result == []:
                        self.path.clear()
                        return self.path

                    self.path.extend(result)
                    self.path.append(finish)
                    self.show_exceptions()
                    return self.path
                
                else:
                    for link in page_links:
                        page_title = link.get("title", "")
                        self.graph[page_title] = page_links
                        self.search_queue.put(page_title)

            except Exception as e:
                self.exceptions.put(e)

    def show_exceptions(self) -> None:
        while not self.exceptions.empty():
            logging.error(self.exceptions.get())

    def has_finish_link(self, page_name: str, finish: str) -> bool:
        titles = [link.get("title", "") for link in self.graph[page_name]]
        return finish in titles

    def get_page_links(self, page_url: str) -> set[element.Tag]:
        soup = self.get_soup(page_url)

        body_content = soup.select("div.mw-content-ltr")[0]
        page_links = body_content.find_all("a", class_=lambda cls: cls is None)
        validated_page_links = filter(self.validate_link, page_links)
        unique_page_links = list(dict.fromkeys(validated_page_links))

        return unique_page_links[:LINKS_PER_PAGE]

    def get_soup(self, page_url: str) -> BeautifulSoup:
        if page_url in self.visited_pages:
            raise AlreadyVisitedException(
                f"Page {page_url} is already visited!"
            )

        response = self.visit_page(page_url)
        return BeautifulSoup(response.text, "html.parser")

    def visit_page(self, page_url: str, depth: int = 0) -> requests.Response:
        if depth > 3:
            raise ResourceAccessException(f"Cannot acceess page {page_url}")

        try:
            response = requests.get(page_url)
            self.visited_pages.add(page_url)
        except requests.exceptions.RequestException:
            self.visit_page(page_url, depth=depth+1)
        finally:
            time.sleep(60 / REQUESTS_PER_MINUTE)

        return response

    @staticmethod
    def validate_link(link: element.Tag) -> bool:
        valid_links_regex = '(https://en.wikipedia.org)?/wiki/.*'
        href = link.get("href", "")

        if re.match(valid_links_regex, href) and ":" not in href:
            return True
