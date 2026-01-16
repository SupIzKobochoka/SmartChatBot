from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

def get_vector_store(device='cuda', persist_directory="database/chroma/"):
    embeder_name = 'intfloat/multilingual-e5-large'
    query = 'query: '
    passage = 'passage: '

    embeder = HuggingFaceBgeEmbeddings(model_name=embeder_name,
                                    model_kwargs={'device':device},
                                    query_instruction=query,
                                    embed_instruction=passage,
                                    encode_kwargs={'batch_size': 5}
                                    )

    vector_store = Chroma(
        collection_name="example_collection",
        embedding_function=embeder,
        persist_directory=persist_directory,
    )
    
    return vector_store