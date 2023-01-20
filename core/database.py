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


def connect_to_db(user, password, host, port, db_name):
    db_str = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}'

    engine = create_engine(db_str)
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)

    return session, engine


def page_in_db(session: Session, page_title: str) -> (Page | None):
    return session.query(Page).filter(
        Page.title == page_title
    ).first()


def cached_page_db(session: Session, page_title: str) -> (Page | None):
    page = page_in_db(session, page_title)

    if page is not None:
        if page.right_pages.all():
            return page


def save_page_with_links(
    session: Session, page_title: str, links: list[str]
) -> Page:
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
    links = page.right_pages
    return session.query(links.filter(
        Page.title == finish
    ).exists()).scalar()


def get_page_links(page: Page) -> list[str]:
    return [link.title for link in page.right_pages]
