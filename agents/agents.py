from langchain.agents import create_agent
from .utils import get_llm, EndAgent
from tools import (get_simular_docs,
                   get_employee_activity_log_from_db,
                   add_employee_activity_log_to_db, 
                   del_employee_activity_log_from_db,
                   DOC_TOOLS) 
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool
         

# MEMORY = MemorySaver()

docAgent = create_agent(model=get_llm(),
                        system_prompt=(
                            ('Ты — умный помощник по созданию документов.\n'
                             'Тебе передаётся история диалога (messages). Используй её как контекст.\n'
                             'Если информация уже есть в истории — не спрашивай её повторно.\n'
                             'ПРАВИЛА:\n'
                             '1. Текст документа НИКОГДА не пиши в ответе.\n'
                             '2. Документ создаётся ТОЛЬКО через вызов инструмента.\n'
                             '3. Если данных не хватает — задай уточняющие вопросы.\n'
                             '4. Если данных достаточно — сразу вызывай инструмент.\n'
                             '5. Если пользователь просит написать текст — сформируй его и передай ВНУТРИ tool.\n'
                             '6. Если формулировка разумна, но слегка неоднозначна — выбери наиболее очевидную интерпретацию и НЕ задавай вопросов\n'
                             'Любой другой формат ответа — ошибка.')
                             ),
                        tools=[*DOC_TOOLS]
                        )

ragAgent = create_agent(model=get_llm(),
                        system_prompt=(
                           "Ты агент поиска в базе знаний. "
                           "Отвечай только на основе найденных данных. "
                           "Если данных нет или их недостаточно — так и скажи. "
                           "Ничего не добавляй от себя."
                        ),
                        tools=[get_simular_docs]
                        )

activityAgent = create_agent(model=get_llm(),
                             system_prompt=(
                                "Роль: агент БД посещаемости. "
                                "Любые операции выполняй только через инструменты. "
                                "При отсутствии обязательных параметров — задай вопросы. "
                                "Свободный текст запрещён."
                             ),
                             tools=[get_employee_activity_log_from_db, 
                                    add_employee_activity_log_to_db, 
                                    del_employee_activity_log_from_db]
                             )

agents = {'docAgent': docAgent, 
          'ragAgent': ragAgent, 
          'activityAgent': activityAgent
          }

endAgent = EndAgent()
domenAgent = lambda x: True # TODO написать агента, который проверяет смену домена, в идеале просто дообучть классификатор текста на домен


