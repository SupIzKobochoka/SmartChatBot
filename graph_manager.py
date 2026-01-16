from graph import aGraph
from langgraph.checkpoint.memory import MemorySaver

class GraphSessionManager:
    def __init__(self):
        self.memory = MemorySaver()
        self.graph = aGraph(self.memory).compile()
        self.users = set()
    
    async def __call__(self, 
                       message: str, 
                       id: str
                       ) -> str:
        if id not in self.users:
            res = await self.graph.first_run(message, thread_id=id, return_last=False)
            self.users.add(id)
            return res['__interrupt__'][0].value['message'], res['__interrupt__'][0].value.get('paths', [])
        
        res = await self.graph.other_run(message, thread_id=id, return_last=False)
        return res['__interrupt__'][0].value['message'], res['__interrupt__'][0].value.get('paths', [])
    
    def delete_id(self, id: str):
        if id in self.users:
            self.users.remove(id)
            self.memory.delete_thread(thread_id=id)