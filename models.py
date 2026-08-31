from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
)

from sqlalchemy.orm import relationship

from database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(String, nullable=True)
    author = Column(String, nullable=True)

    publisher = Column(
        String,
        nullable=True,
    )

    source_publisher = Column(
        String,
        nullable=True,
    )

    publication_year = Column(
        String,
        nullable=True,
    )

    isbn = Column(
        String,
        nullable=True,
    )

    price = Column(
        Float,
        nullable=True,
    )

    currency = Column(
        String,
        nullable=True,
    )

    subject = Column(
        String,
        nullable=True,
    )

    language = Column(
        String,
        nullable=True,
    )

    vendor = Column(
        String,
        nullable=True,
    )

    source_file = Column(
        String,
        nullable=True,
    )

    source_sheet = Column(
        String,
        nullable=True,
    )

    validation_status = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    selection_items = relationship(
        "SelectionItem",
        back_populates="book",
    )


class Selector(Base):
    __tablename__ = "selectors"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    full_name = Column(
        String,
        nullable=False,
    )

    user_id = Column(
        String,
        nullable=True,
    )

    department = Column(
        String,
        nullable=True,
    )

    email = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    carts = relationship(
        "SelectionCart",
        back_populates="selector",
    )


class SelectionCart(Base):
    __tablename__ = "selection_carts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    selector_id = Column(
        Integer,
        ForeignKey("selectors.id"),
        nullable=False,
    )

    status = Column(
        String,
        default="Submitted",
    )

    submitted_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    selector = relationship(
        "Selector",
        back_populates="carts",
    )

    items = relationship(
        "SelectionItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )


class SelectionItem(Base):
    __tablename__ = "selection_items"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    cart_id = Column(
        Integer,
        ForeignKey("selection_carts.id"),
        nullable=False,
    )

    book_id = Column(
        Integer,
        ForeignKey("books.id"),
        nullable=False,
    )

    requested_quantity = Column(
        Integer,
        default=1,
    )

    admin_approved_quantity = Column(
        Integer,
        default=0,
    )

    admin_status = Column(
        String,
        default="Pending",
    )

    admin_note = Column(
        Text,
        nullable=True,
    )

    cart = relationship(
        "SelectionCart",
        back_populates="items",
    )

    book = relationship(
        "Book",
        back_populates="selection_items",
    )