import logging
import queue
import re
import time

import requests
from bs4 import BeautifulSoup, element
from database import (cached_page_db, connect_to_db, get_page_links,
                      has_finish_link, save_page_with_links)
from exceptions import AlreadyVisitedException, ResourceAccessException

REQUESTS_PER_MINUTE = 100
LINKS_PER_PAGE = 200
SEARCH_DEPTH = 3


class WikiRacer:
    """Finds the path from start to finish article in Wikipedia.

    Raises:
        AlreadyVisitedException: page is viseted
        ResourceAccessException: cannot access the server
    """

    base_wikipedia_url = "https://uk.wikipedia.org"

    def __init__(self, depth: int = 0):
        """Initialize an object.

        Args:
            depth (int, optional): shows current depth of recursion.
            Defaults to 0.
        """
        self.depth = depth
        self.path = None
        self.visited_pages = None

        self.session, self.engine = connect_to_db(
            "postgres", "postgres", "localhost", 5432, "wiki"
        )

    def find_path(self, start: str, finish: str) -> list[str]:
        """Finds the path from start page to finish page.

        Uses the links from pages to come to desired point.

        Args:
            start (str): title of the first page in Wikipedia
            finish (str): title of the last page in Wikipedia

        Returns:
            list[str]: path from start to finish
        """
        # check if start and finish are valid article title
        self.visit_page(self.base_wikipedia_url + "/wiki/" + finish)
        self.visit_page(self.base_wikipedia_url + "/wiki/" + finish)

        if self.depth > SEARCH_DEPTH:
            return []

        if start == finish:
            return [start]

        self.path = []
        self.search_queue = queue.Queue()
        self.visited_pages = set()

        self.search_queue.put(start)

        while not self.search_queue.empty() and self.depth < SEARCH_DEPTH:
            try:
                current_page = self.search_queue.get()
                print(current_page)
                cached_page = cached_page_db(self.session, current_page)

                if cached_page is None:
                    page_url = (
                        self.base_wikipedia_url + "/wiki/" + current_page
                    )

                    try:
                        page_links = self.get_page_links(page_url)
                    except AlreadyVisitedException:
                        continue

                    cached_page = save_page_with_links(
                        self.session, current_page, page_links
                    )

                else:
                    page_links = get_page_links(cached_page)

                if has_finish_link(self.session, cached_page, finish):
                    racer = WikiRacer(depth=self.depth+1)
                    result = racer.find_path(start, finish=current_page)

                    if result == []:
                        self.path.clear()
                        return self.path

                    self.path.extend(result)
                    self.path.append(finish)
                    return self.path

                else:
                    for link in page_links:
                        self.search_queue.put(link)

            except Exception as e:
                logging.exception(e)

        return []

    def get_page_links(self, page_url: str) -> list[element.Tag]:
        """Return the list links in webpage.

        Args:
            page_url (str): url of the desired webpage

        Returns:
            list[element.Tag]: list of <a> tags in webpage
        """
        soup = self.get_soup(page_url)

        body_content = soup.select("div.mw-content-ltr")[0]
        page_links = body_content.find_all("a", class_=lambda cls: cls is None)
        validated_page_links = filter(self.validate_link, page_links)
        unique_page_links = list(dict.fromkeys(validated_page_links))
        titles = list(
            map(lambda link: link.get("title", ""), unique_page_links)
        )

        return titles[:LINKS_PER_PAGE]

    def get_soup(self, page_url: str) -> BeautifulSoup:
        """Parses the HTML of desired webpage.

        Args:
            page_url (str): url of webpage to parse

        Returns:
            BeautifulSoup: parsed HTML
        """
        if page_url in self.visited_pages:
            raise AlreadyVisitedException(
                f"page {page_url} is already visited!"
            )

        response = self.visit_page(page_url)
        return BeautifulSoup(response.text, "html.parser")

    def visit_page(self, page_url: str, depth: int = 0) -> requests.Response:
        """Visits the page and waits some time.

        Args:
            page_url (str): page to visit
            depth (int, optional): times retried to send a request.
            Defaults to 0.

        Raises:
            AlreadyVisitedException: when page was already visited
            ResourceAccessException: can't get response from the server

        Returns:
            requests.Response: _description_
        """
        if depth > 3:
            raise ResourceAccessException(f"Cannot acceess page {page_url}")

        try:
            response = requests.get(page_url)
            if response.status_code != 200:
                raise requests.exceptions.RequestException

            self.visited_pages.add(page_url)

        except requests.exceptions.RequestException:
            self.visit_page(page_url, depth=depth+1)

        finally:
            time.sleep(60 / REQUESTS_PER_MINUTE)

        return response

    @staticmethod
    def validate_link(link: element.Tag) -> bool:
        """Validates the link.

        Ignores external links and technical links about article.

        Args:
            link (element.Tag): parsef <a> tag

        Returns:
            bool: shows if link is valid
        """
        valid_links_regex = '(https://en.wikipedia.org)?/wiki/.*'
        href = link.get("href", "")

        if re.match(valid_links_regex, href) and ":" not in href:
            return True
