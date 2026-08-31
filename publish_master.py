import sys
import pandas as pd

from database import SessionLocal
from models import Book


def clean_value(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    if text == "":
        return None

    return text


def clean_price(value):
    if pd.isna(value):
        return None

    try:
        return float(
            str(value)
            .replace(",", "")
            .strip()
        )

    except Exception:
        return None


def publish_master(file_path):
    print("Reading Master Acquisition workbook...")

    df = pd.read_excel(
        file_path,
        sheet_name="Master Acquisition",
    )

    print(
        f"Records found: {len(df)}"
    )

    db = SessionLocal()

    imported = 0
    skipped = 0

    try:
        for _, row in df.iterrows():

            title = clean_value(
                row.get("Title")
            )

            author = clean_value(
                row.get("Author")
            )

            # Do not publish completely empty
            # bibliographic records.
            if not title and not author:
                skipped += 1
                continue

            book = Book(
                title=title,

                author=author,

                publisher=clean_value(
                    row.get("Publisher")
                ),

                source_publisher=clean_value(
                    row.get("Source Publisher")
                ),

                publication_year=clean_value(
                    row.get("Publication Year")
                ),

                isbn=clean_value(
                    row.get("ISBN")
                ),

                price=clean_price(
                    row.get("Price")
                ),

                currency=clean_value(
                    row.get("Currency")
                ),

                subject=clean_value(
                    row.get("Subject")
                ),

                language=clean_value(
                    row.get("Language")
                ),

                vendor=clean_value(
                    row.get("Vendor")
                ),

                source_file=clean_value(
                    row.get("Source File")
                ),

                source_sheet=clean_value(
                    row.get("Source Sheet")
                ),

                validation_status=clean_value(
                    row.get("Validation Status")
                ),
            )

            db.add(book)
            imported += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    print("")
    print(
        "AcquiAI publication complete."
    )
    print(
        f"Imported books: {imported}"
    )
    print(
        f"Skipped records: {skipped}"
    )


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print(
            "Usage:"
        )

        print(
            'python publish_master.py '
            '"multi_publisher_master_acquisition.xlsx"'
        )

        sys.exit(1)

    publish_master(
        sys.argv[1]
    )