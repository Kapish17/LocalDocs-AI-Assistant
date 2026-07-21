from pathlib import Path

from utils.file_scanner import scan_folder
from loaders.loader_manager import load_document
from rag.chunking import split_documents
from rag.vector_store import create_vector_store
from rag.retriever import get_retriever
from rag.prompt import RAG_PROMPT
from llm.gemini import get_llm


VECTOR_DB_PATH = Path("database/faiss_index")


def build_vector_store():

    files = scan_folder("data")

    if not files:
        print("❌ No supported documents found.")
        return

    documents = []

    print("\nLoading documents...\n")

    for file in files:
        try:
            document = load_document(file)

            if document:
                documents.append(document)
                print(f"✅ Loaded: {file.name}")

        except Exception as e:
            print(f"❌ Failed: {file.name}")
            print(e)

    print("\nSplitting documents...\n")

    chunks = split_documents(documents)

    print(f"📄 Documents : {len(documents)}")
    print(f"🧩 Chunks    : {len(chunks)}")

    create_vector_store(chunks)


def main():

    print("=" * 60)
    print("LocalDocs AI Assistant")
    print("=" * 60)

    # Create FAISS only once
    if not VECTOR_DB_PATH.exists():

        print("\nNo FAISS database found.")
        print("Creating a new vector database...\n")

        build_vector_store()

    else:
        print("✅ Existing FAISS database found.")

    retriever = get_retriever()

    llm = get_llm()

    print("\n====================================")
    print("LocalDocs AI Assistant Ready!")
    print("Type 'exit' to quit.")
    print("====================================")

    while True:

        question = input("\nAsk: ")

        if question.lower() == "exit":
            break

        # Retrieve relevant chunks
        docs = retriever.invoke(question)

        print("\n========== Retrieved Chunks ==========\n")

        for i, doc in enumerate(docs, start=1):
            print(f"Chunk {i}")
            print(f"Source : {doc.metadata.get('source')}")
            print("-" * 60)
            print(doc.page_content[:400])
            print("-" * 60)

        # Create context
        context = "\n\n".join(
            doc.page_content for doc in docs
        )

        # Build prompt
        prompt = RAG_PROMPT.format(
            context=context,
            question=question
        )

        # Get LLM response
        response = llm.invoke(prompt)

        print("\n========== Answer ==========\n")

        if isinstance(response.content, list):
            for block in response.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    print(block["text"])
        else:
            print(response.content)


if __name__ == "__main__":
    main()