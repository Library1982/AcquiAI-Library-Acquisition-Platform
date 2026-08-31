# AcquiAI — AI Library Acquisition Platform

AcquiAI is a bilingual English/Arabic library acquisition workflow platform designed to simplify publisher file processing, book selection, approval, and publisher purchasing.

Designed & Developed by **Yameen Abdullah**

## Main Workflow

1. Upload multiple publisher/vendor Excel files.
2. AcquiAI standardizes and combines them into one Master Acquisition Catalogue.
3. Duplicate titles are consolidated.
4. The generated master catalogue is published to the Selection Portal.
5. Students and staff search and select recommended books.
6. Admin receives aggregated selections.
7. Admin can approve/reject titles individually or in bulk.
8. Final approved quantities are prepared.
9. AcquiAI generates the Final Purchase Master.
10. Approved titles are automatically separated into individual publisher/vendor Excel order files inside a ZIP package.

## Key Features

- English and Arabic bilingual interface
- Arabic RTL support
- Multiple `.xlsx` / `.xls` publisher file upload
- Automatic header-row detection
- Arabic and English bibliographic field mapping
- ISBN, publication year and price validation
- Publisher/source tracking
- Duplicate consolidation
- Master Acquisition Catalogue generation
- User book selection portal
- Search, publisher, language and subject filters
- Pagination for large catalogues
- Aggregated demand by unique title
- Requested-by user count
- Individual and bulk approval/rejection
- Final purchasing quantity management
- Final Approved Order Excel export
- Separate publisher/vendor purchase order files
- Publisher Orders ZIP export
- Modern responsive Admin Dashboard
- SQLite prototype database

## Technology

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pandas
- OpenPyXL
- HTML/CSS/JavaScript

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt