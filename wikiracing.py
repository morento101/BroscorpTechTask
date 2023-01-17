import logging
import queue
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event, Lock

import requests
from bs4 import BeautifulSoup, element

REQUESTS_PER_MINUTE = 100
LINKS_PER_PAGE = 200


class AlreadyVisitedException(Exception):
    pass


class ResourceAccessException(Exception):
    pass


class WikiRacer:
    base_wikipedia_url = "https://uk.wikipedia.org"
    lock = Lock()

    def __init__(self):
        self.graph = None
        self.path = None
        self.visited_pages = None
        self.exceptions = None

    def find_path(self, start: str, finish: str) -> list[str]:
        self.graph = {}
        self.path = []
        self.visited_pages = set()
        self.exceptions = queue.Queue()

        starting_page = self.base_wikipedia_url + "/wiki/" + start
        starting_page_links = self.get_page_links(starting_page)
        self.graph[start] = starting_page_links

        if self.has_finish_link(start, finish):
            self.path.extend((start, finish))

        else:
            event = Event()
            with ThreadPoolExecutor() as ex:
                futures = []

                for link in self.graph[start]:
                    future = ex.submit(
                        self.process_the_child_link,
                        event,
                        link=link,
                        start=start,
                        finish=finish
                    )
                    futures.append(future)

                for future in as_completed(futures):
                    result = future.result()

                    if result is not None:
                        break

        while not self.exceptions.empty():
            logging.error(self.exceptions.get())

        return self.path

    def process_the_child_link(
        self, event: Event, link: element.Tag, start: str, finish: str
    ) -> None:

        try:
            if event.is_set():
                return

            page_url = self.base_wikipedia_url + link.get("href", "")
            page_links = self.get_page_links(page_url)
            page_title = link.get("title", "")
            self.graph[page_title] = page_links

            if self.has_finish_link(page_title, finish) and not event.is_set():
                event.set()

                with self.lock:
                    self.path.extend((start, page_title, finish))

                return page_title

        except Exception as e:
            self.exceptions.put(e)

    def has_finish_link(self, page_name: str, finish: str) -> bool:
        titles = [link.get("title", "") for link in self.graph[page_name]]
        return finish in titles

    def get_page_links(self, page_url: str) -> set[element.Tag]:
        soup = self.get_soup(page_url)

        body_content = soup.select("div.mw-content-ltr")[0]
        page_links = body_content.find_all("a", class_=lambda cls: cls is None)
        page_links = page_links

        return set(filter(self.validate_link, page_links))

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
