from agents import (AGENTS, # уже всех содержит
                    # docAgent,
                    # ragAgent,
                    # activityAgent,
                    # domenAgent,
                    endAgent,
                    )
from typing import Literal, Annotated, Any
from langgraph.graph import StateGraph, MessagesState, END
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from agents.utils import get_llm
from agents import ask_agent, endAgent
from tools.document_template import DOC_NAMES
from pathlib import Path
from tools.document_template.constants import CURRENT_THREAD_ID

mainAgent_PROMPT = (
    "Ты агент-дирижёр. Общайся с пользователем и маршрутизируй запросы. "
    "Единственный инструмент: ask_agent(agent_name, message). "
    "agent_name строго: docAgent | ragAgent | activityAgent. "
    "Правила: документы/заявления/шаблоны -> docAgent; поиск по базе знаний/политики/регламенты -> ragAgent; посещаемость/логи/добавить/удалить/исправить запись -> activityAgent. "
    "Ты не ответственнен за области агентов, если у пользователя есть вопрос на эти темы - вызывай агентво . "
    "Не придумывай аргументы и не вызывай tool, если не уверен."
)
mainAgent = get_llm().bind_tools([ask_agent])

class State(MessagesState):
    # messages: list # глобальная память main агента
    curent_agent: str
    agent_history: list[BaseMessage] # история малых агента
    value: Any # Значение из последней ноды
    metadata: dict[Any, Any]
    id_: str
    paths: list[str]

async def ckeckerNode(state: State):
    is_end = await endAgent.ainvoke(state['value'])
    if is_end:
        value = state['value']
        return Command(update={'messages': ToolMessage(f'Пользоветель попросил закончить выполнение со следующими словами: {value}', 
                                                       tool_call_id=state['messages'][-1].tool_calls[0]['id'])},
                       goto='mainAgentNode')
    else:
        return Command(goto='callAgentNode')

async def mainAgentNode(state: State):
    messages = [mainAgent_PROMPT] + state['messages']
    return {'value': await mainAgent.ainvoke(messages)}

def mainAgentNodeRouter(state: State):
    message = state['value']
    if message.tool_calls:
        return Command(update={'messages': message,
                               'agent_history': [],
                               'curent_agent': 'mainAgentNode',
                               'paths': []
                               },
                       goto='callAgentNode')
    else:
        return Command(update={'messages': message,
                               'curent_agent': 'mainAgentNode',
                               'paths': []
                               },
                       goto='askHumanNode')

async def callAgentNode(state: State):
    if state['curent_agent'] == 'mainAgentNode':
        agent_name = state['value'].tool_calls[0]['args']['agent_name']
        message = state['value'].tool_calls[0]['args']['message']
        res = await AGENTS[agent_name].ainvoke({'messages': HumanMessage(message)}) # ask_agent.invoke(state['value'].tool_calls[0])
    else:
        agent_name = state['curent_agent']
        message = state['agent_history']
        res = await AGENTS[agent_name].ainvoke({'messages': message}) # ask_agent.invoke(state['agent_history'])
    return {'value': res['messages'],
            'curent_agent': agent_name}

def callAgentNodeRouter(state: State):
    if any(map(lambda x: isinstance(x, ToolMessage), state['value'])):
        value_tool = ToolMessage(state['value'][-1].content, tool_call_id=state['messages'][-1].tool_calls[0]['id'])
        value_ai = AIMessage(state['value'][-1].content)
        
        # Это должно делаться на уровне агентов, но я не заложил это изначально, поэтому так :(
        if state['curent_agent'] == 'docAgent':
            # обрабатываю возможность создания нескольких доков, но на самом деле, 
            # оно не будет корректно работать, потому что изначально логику так не задал, а переписывать лень)
            tool_names = map(lambda x: x.name, filter(lambda x: isinstance(x, ToolMessage), state['value']))
            paths = [str(Path('docs_generated') / state['id_'] / DOC_NAMES[tool_name]) for tool_name in tool_names]

            return Command(update={'messages': [value_tool, value_ai],
                                   'curent_agent': 'mainAgentNode',
                                   'paths': paths,
                                   },
                          goto='askHumanNode')

        return Command(update={'messages': [value_tool, value_ai],
                               'curent_agent': 'mainAgentNode',
                               },
                       goto='askHumanNode')
    else:
        return Command(update={'agent_history': state.get('agent_history', []) + state['value']},
                       goto='askHumanNode')

def askHumanNode(state: State):
    if state['curent_agent'] == 'mainAgentNode':
        message = state['messages'][-1].content
    else:
        message = state['value'][-1].content
    answer = interrupt({'message': message, 'paths': state['paths']})
    return {'value': answer}

def askHumanNodeRouter(state: State):
    if state['curent_agent'] == 'mainAgentNode':
        value = HumanMessage(state['value'])
        return Command(update={'messages': value},
                       goto='mainAgentNode')
    else:
        value = HumanMessage(state['value'])
        return Command(update={'agent_history': state.get('agent_history', []) + [value]},
                       goto='ckeckerNode')

def get_graph(checkpointer):
    g = StateGraph(State)
    g.add_node('mainAgentNode', mainAgentNode) # В mainAgentNodeRouter
    g.add_node('mainAgentNodeRouter', mainAgentNodeRouter) # В callAgentNode или askHumanNode
    g.add_node('askHumanNode', askHumanNode) # В askHumanNodeRouter
    g.add_node('askHumanNodeRouter', askHumanNodeRouter) # В ckeckerNode или в mainAgentNode
    g.add_node('ckeckerNode', ckeckerNode) # В mainAgentNode или в callAgentNode
    g.add_node('callAgentNode', callAgentNode) # В callAgentNodeRouter
    g.add_node('callAgentNodeRouter', callAgentNodeRouter) # В mainAgentNode или в askHumanNode

    g.add_edge('mainAgentNode', 'mainAgentNodeRouter')
    g.add_edge('askHumanNode', 'askHumanNodeRouter')
    g.add_edge('callAgentNode', 'callAgentNodeRouter')

    g.set_entry_point('mainAgentNode')
    graph = g.compile(checkpointer=checkpointer)
    return graph

class aGraph:
    def __init__(self, checkpointer):
        self.memory = checkpointer
    
    def compile(self):
        if self.memory:
            self.graph = get_graph(self.memory)
            return self
        else:
            self.graph = get_graph(self.memory)
            return self
        
    async def first_run(self, 
                  message: str, 
                  thread_id: str,
                  return_last: bool = True
                  ) -> str:
        config = {"configurable": {"thread_id": thread_id}}

        _ = CURRENT_THREAD_ID.set(thread_id)
        try:
            res = await self.graph.ainvoke({'messages': HumanMessage(message), 'id_': thread_id}, config=config)
        except Exception as e:
            raise e
        finally:
            CURRENT_THREAD_ID.reset(_)
        
        if return_last: 
            return res['__interrupt__'][0].value['message']
        return res
    
    async def other_run(self, 
                  message: str, 
                  thread_id: str,
                  return_last: bool = True
                  ) -> str:
        config = {"configurable": {"thread_id": thread_id}}

        _ = CURRENT_THREAD_ID.set(thread_id)
        try:
            res = await self.graph.ainvoke(Command(resume=message), config=config)
        except Exception as e:
            raise e
        finally:
            CURRENT_THREAD_ID.reset(_)

        if return_last: 
            return res['__interrupt__'][0].value['message']
        return res