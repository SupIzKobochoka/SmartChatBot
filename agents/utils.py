from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

openai_api_key = 'sk-e59mvbb9gcip0mjqea8qdf6mkyf8k8nhgs9i55k7d8zdsqxz'
model_name = 'mimo-v2-flash'
openai_api_base = 'https://api.xiaomimimo.com/v1'

openai_api_key = os.getenv('openai_api_key')
model_name = os.getenv('model_name')
openai_api_base = os.getenv('openai_api_base')

def get_llm():
    return ChatOpenAI(
        openai_api_key=openai_api_key,
        model_name=model_name,
        openai_api_base=openai_api_base
    )

@tool
def finish_check(is_end: bool):
    '''is_end=True - Пользователь хочет захончить диалог, иначе False'''
    return is_end

class EndAgent:
    '''Определяет, просит ли пользователь закончить диалог'''
    def __init__(self, 
                 llm = None, 
                 system_prompt: str = None,
                 retryes: int = 3
                 ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.retryes = retryes

        if self.llm is None:
            self.llm = get_llm()

        if self.system_prompt is None:
            self.system_prompt = SystemMessage(
                "Вызови finish_check: "
                "True — если пользователь завершает диалог; "
                "False — если он отвечает и передаёт данные. "
                "Без текста.")
        
        self.llm = self.llm.bind_tools([finish_check], tool_choice=finish_check.name)

    def invoke(self, message: HumanMessage):
        for _ in range(self.retryes):
            result = self.llm.invoke([self.system_prompt,
                                      message])
            if result.tool_calls:
                return result.tool_calls[0]['args']['is_end']
        return result
    
    async def ainvoke(self, message: HumanMessage):
        for _ in range(self.retryes):
            result = await self.llm.ainvoke([self.system_prompt,
                                             message])
            if result.tool_calls:
                return result.tool_calls[0]['args']['is_end']
            return result
    
    def __getattr__(self, name):
        return getattr(self.llm, name)

def is_end(state: dict):
    '''Определяет, просит ли человек закончить'''
    end = EndAgent().invoke(state['messages'][-1])
    if end:
        return Command(goto=END)
    return Command(goto='agent')

class BaseGrapgAgent:
    def __init__(self, 
                 llm,
                 tools: list,
                 system_prompt: str,
                 ):
        self.llm = llm.bind_tools(tools, tool_choice=True)
        self.tool = tools
        self.system_prompt = system_prompt

    def __call__(self, state: MessagesState):
        result = self.llm.invoke([self.system_prompt] + state['messages'])
        return {'messages': result}

def parse_tool_calls(messages: dict[list]):
    '''
    Определяет, куда идти агенту
        1 - Если агент вызвал tool_call, то в tools
        2 - Если агент не вызвал tool_call и вызывал ранее, то отправляем в END
        3 - Если агент не вызвал tool_call и не вызывал ранее, то отправлем в message_to_human последнее сообщение
        
    '''
    messages = messages['messages']
    if messages[-1].tool_calls and len(messages) != 1:
        return 'tools'
    
    if any(map(lambda x: isinstance(x, ToolMessage), messages)):
        return END
    
    return 'message_to_human'

def create_react_graph(tools: list,
                       checkpointer,
                       ask_func=input,
                       llm=None,
                       system_prompt=('Ты полезный помощник, который имеет доступ к инструментам'),
                       ):
    '''
    ReAct агент с возможностью спрашивать у пользователя
    ask_func - принимает сообщение llm, возвращает ответ
    '''
    def message_to_human(state: dict):
        '''Передает сообщение пользователю'''
        answer = ask_func(state["messages"][-1].content)
        return  {"messages": [HumanMessage(content=answer)]}
    
    agent = BaseGrapgAgent(llm=llm, tools=tools, system_prompt=system_prompt)

    g = StateGraph(MessagesState)
    g.add_node('tools', ToolNode(tools=tools))
    g.add_node('agent', agent)
    g.add_node('message_to_human', message_to_human)
    g.add_node('is_end', is_end)
    g.add_edge('tools', 'agent')
    g.add_conditional_edges('agent',
                            parse_tool_calls
                            )
    g.add_edge('message_to_human', 'is_end')
    g.set_entry_point('agent')
    graph = g.compile()

    return graph
