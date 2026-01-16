if __name__ == '__main__':
    # Добавляет данные из базы знаний в векторную базу
    
    from langchain_community.document_loaders import DirectoryLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from vector_store import get_vector_store

    def add_all_data(data_path: str, persist_directory: str, device: str = 'cuda'):
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        parser = DirectoryLoader(path=data_path, exclude='**/*.py') # Желательно проверить, что с .py работает
        docs = parser.load_and_split(splitter)
        vector_store = get_vector_store(device)
        vector_store.add_documents(documents=docs,
                                   persist_directory=persist_directory)

    add_all_data(data_path='knowledge_base/', persist_directory="chroma/")
