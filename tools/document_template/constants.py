from pathlib import Path
from contextvars import ContextVar

CURRENT_THREAD_ID = ContextVar("thread_id")

CONSTANTS = {
'organization': "ООО «Ромашка»",
'position_to': "Генеральному директору",
'full_name_to': "Иванову Ивану Ивановичу",
"output_path": lambda: Path("docs_generated") / CURRENT_THREAD_ID.get()
}