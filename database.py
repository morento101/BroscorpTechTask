from sqlalchemy import (Column, ForeignKey, Integer, String, Table,
                        create_engine)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

article_to_article = Table(
    "arcticle_to_article", Base.metadata,
    Column(
        "left_article_id", Integer, ForeignKey("article.id"), primary_key=True
    ),
    Column(
        "right_article_id", Integer, ForeignKey("article.id"), primary_key=True
    )
)


class Article(Base):
    __tablename__ = 'article'
    id = Column(Integer, primary_key=True)
    label = Column(String)
    right_articles = relationship(
        "article",
        secondary=article_to_article,
        primaryjoin=id==article_to_article.c.left_article_id,
        secondaryjoin=id==article_to_article.c.right_article_id,
        backref="left_articles"
    )


def connect_to_db(user, password, host, port, db_name):
    db_str = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}'
    
    engine = create_engine(db_str)
    session = sessionmaker(bind=engine)()
    Base.metadata.create_all(engine)

    return session, engine
