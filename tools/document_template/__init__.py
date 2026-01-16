from .date_transfer import create_vacation_transfer_doc
from .day_off import create_day_off_doc
from .vacation import create_vacation_doc

DOC_TOOLS = [
    create_vacation_transfer_doc, 
    create_day_off_doc, 
    create_vacation_doc
    ]

DOC_NAMES = {
create_vacation_transfer_doc.name: "vacation_transfer_statement.docx",
create_day_off_doc.name: "day_off.docx",
create_vacation_doc.name: "vacation.docx"
}