from .agents import (docAgent,
                     ragAgent,
                     activityAgent,
                     endAgent,
                     domenAgent,
                    #  MEMORY
                     )
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from typing import Literal

AGENTS = {'docAgent': docAgent, 
          'ragAgent': ragAgent, 
          'activityAgent': activityAgent,
          'endAgent': endAgent,
          'domenAgent': domenAgent
        }

@tool
def ask_agent(agent_name: Literal['docAgent', 
                                  'ragAgent', 
                                  'activityAgent'],
              message: str
             ): 
    '''
    Послать сообщение агенту
    - agent_name: Literal['docAgent', 'ragAgent', 'activityAgent']
        docAgent - агент, который умеет создавать документы
        ragAgent - агент, который умеет искать данные в базе знаний
        activityAgent - агент, который умеет работать с данными в базе посещаемости
    - message: str
    '''
    result = AGENTS[agent_name].invoke({'messages': HumanMessage(message)})
    return result

# в целом используется долько как схема, поэтому нет смысла в асинхронной 
@tool
async def aask_agent(agent_name: Literal['docAgent', 
                                  'ragAgent', 
                                  'activityAgent'],
              message: str
             ): 
    '''
    Послать сообщение агенту
    - agent_name: Literal['docAgent', 'ragAgent', 'activityAgent']
        docAgent - агент, который умеет создавать документы
        ragAgent - агент, который умеет искать данные в базе знаний
        activityAgent - агент, который умеет работать с данными в базе посещаемости
    - message: str
    '''
    result = await AGENTS[agent_name].ainvoke({'messages': HumanMessage(message)})
    return result