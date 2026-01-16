from pydantic import BaseModel, field_validator
from database.vector_store import get_vector_store
from langchain.tools import tool
from pydantic import Field
from datetime import date, time

import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extras import RealDictCursor 

from .document_template import DOC_TOOLS
from .utils import fio_to_nominative

# from langchain_community.tools import (
#     WikipediaQueryRun,
#     ArxivQueryRun,
#     DuckDuckGoSearchRun
# )

VECTOR_STORE = get_vector_store()
K = 5

class GetDocsArgs(BaseModel):
    query: str

@tool(args_schema=GetDocsArgs)
def get_simular_docs(**data) -> str:
    '''
    Возвращает список релевантных документов из базы знаний. 
    Обязательно возвращай пользователю, из какого документа был взят ответ
    '''
    results = VECTOR_STORE.similarity_search(query=data['query'], k=K)
    return '\n\n'.join(f'Документ #{ind+1}:\nmetadata: {doc.metadata}\npage_content: {doc.page_content}' 
                       for ind, doc in enumerate(results))

# employee_activity_log tools 

conn = psycopg2.connect(
    dbname="daily_log",
    user="postgres",
    password="123",
    host="localhost",
    port=5432
)

cursor = conn.cursor(cursor_factory=RealDictCursor)

class AddRequestArgs(BaseModel):
    PERSON_NAME: str = Field(description='ФИО в именительном падеже человека')
    date_: date
    time_start: time = Field(description='Время начала деятельности')
    time_end: time = Field(description='Время конца деятельности')
    description: str = Field(description='Описание деятельности')
    
    @field_validator("PERSON_NAME", mode="before")
    def _fio_to_nominative(cls, v):
        return fio_to_nominative(v)

class AddRequestsArgs(BaseModel):
    requests: list[AddRequestArgs]

def dicts_to_rows(dicts: list[dict]) -> list[list]:
    '''-> [PERSON_NAME, date_, time_start, time_end, description]'''
    order = ['PERSON_NAME', 'date_', 'time_start', 'time_end', 'description']
    rows = [[
        di[col] for col in order
    ] for di in dicts]
    
    return rows

@tool(args_schema=AddRequestsArgs)
def add_employee_activity_log_to_db(**data):
    '''Добавляет данные о деятельности человека в базу'''
    rows = dicts_to_rows(map(lambda x: x.model_dump(), data['requests']))
    sql_request = '''
    --sql
    INSERT INTO employee_activity_log (PERSON_NAME, date_, time_start, time_end, description)
        VALUES %s
        ;
    '''
    execute_values(cursor, sql_request, rows)
    conn.commit()
    return f'Добавлено {len(rows)} строк'

class GetRequestArgs(BaseModel):
    PERSON_NAME: str = Field(description='ФИО человека в именительном падеже. ОБЯЗАТЕЛЬНО ТОЛЬКО В ИМЕНИТЕЛЬНОМ!')
    date_: date

    @field_validator("PERSON_NAME", mode="before")
    def _fio_to_nominative(cls, v):
        return fio_to_nominative(v)

class GetRequestsArgs(BaseModel):
    requests: list[GetRequestArgs]

@tool(args_schema=GetRequestsArgs)
def get_employee_activity_log_from_db(**data) -> str:
    '''Получает данные о деятельности человека из базы'''
    requests = map(lambda x: x.model_dump(), data['requests'])
    result = []
    for request in requests:
        query = f'''
                --sql
                SELECT * FROM employee_activity_log
                WHERE PERSON_NAME = '{request['PERSON_NAME']}' AND
                      date_ = '{request['date_'].strftime("%Y-%m-%d")}'
                ;
                    '''
        
        cursor.execute(query)
        result.extend(map(dict, cursor.fetchall()))
    return '\n'.join(map(str, result))

class DelRequestArgs(BaseModel):
    id: int

class DelRequestsArgs(BaseModel):
    requests: list[DelRequestArgs]

@tool(args_schema=DelRequestsArgs)
def del_employee_activity_log_from_db(**data) -> str:
    '''
    Удаляет данные о деятельности человека из базы по id. 
    Чтобы узнать id сначала нужно сделать запрос в базу.
    '''
    ids = [i['id'] for i in  map(lambda x: x.model_dump(), data['requests'])]
    query = '''
            --sql 
            DELETE FROM employee_activity_log
            WHERE id = ANY(%s)
            ;
            '''
    cursor.execute(query, (ids,))
    conn.commit()
    return f'Удалено {len(ids)} строк'


TOOLS = [get_simular_docs, # Про базу знаний 
         
         get_employee_activity_log_from_db, # Про данные деятельности сотрудников 
         add_employee_activity_log_to_db, 
         del_employee_activity_log_from_db
         
         ]

