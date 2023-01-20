from sqlalchemy import (Column, ForeignKey, Integer, String, Table,
                        UniqueConstraint, create_engine)
from sqlalchemy.orm import (Session, declarative_base, relationship,
                            sessionmaker)

Base = declarative_base()

page_to_page = Table(
    "page_to_page", Base.metadata,
    Column(
        "left_page_id", Integer, ForeignKey("page.id"), primary_key=True
    ),
    Column(
        "right_page_id", Integer, ForeignKey("page.id"), primary_key=True
    )
)


class Page(Base):
    """Model of the Wikipedia page with links.

    Has the Many-to-many relationship on itself.
    """

    __tablename__ = 'page'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    right_pages = relationship(
        "Page",
        secondary=page_to_page,
        primaryjoin=id == page_to_page.c.left_page_id,
        secondaryjoin=id == page_to_page.c.right_page_id,
        backref="left_pages",
        lazy='dynamic',
    )
    UniqueConstraint("id", "title")


def connect_to_db(
    user: str, password: str, host: str, port: str, db_name: str
):
    """Connects to PostgreSQL database.

    Args:
        user (str)
        password (str)
        host (str)
        port (str)
        db_name (str)
    """
    db_str = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}'

    engine = create_engine(db_str)
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)

    return session, engine


def page_in_db(session: Session, page_title: str) -> (Page | None):
    """Returns page from db if exists.

    Args:
        session (Session)

    Returns:
        Page: page model
    """
    return session.query(Page).filter(
        Page.title == page_title
    ).first()


def cached_page_db(session: Session, page_title: str) -> (Page | None):
    """Checks if page is saved in database with all links.

    Args:
        session (Session)

    Returns:
        Page: page model
    """
    page = page_in_db(session, page_title)

    if page is not None:
        if page.right_pages.all():
            return page


def save_page_with_links(
    session: Session, page_title: str, links: list[str]
) -> Page:
    """Saves page and its links to the database

    Args:
        session (Session)
        page_title (str): title of the page
        links (list[str]): lists of page titles from the <a> tags

    Returns:
        Page: page model
    """
    orm_links = [Page(title=title) for title in links]
    session.add_all(orm_links)

    page_saved = page_in_db(session, page_title)
    if page_saved:
        page_saved.right_pages = orm_links
    else:
        page_saved = Page(title=page_title, right_pages=orm_links)
        session.add(page_saved)

    session.commit()
    return page_saved


def has_finish_link(session: Session, page: Page, finish: str) -> bool:
    """Checks if current page has link to the finish page.

    Args:
        session (Session)
        page (Page): page to check
        finish (str): title of the finish page

    Returns:
        bool
    """
    links = page.right_pages
    return session.query(links.filter(
        Page.title == finish
    ).exists()).scalar()


def get_page_links(page: Page) -> list[str]:
    """Returns titles of the pages in desired article

    Args:
        page (Page): model of the desired page

    Returns:
        list[str]: list of link's titles
    """
    return [link.title for link in page.right_pages]
