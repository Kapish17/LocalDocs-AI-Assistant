from pathlib import Path

from rag.index_builder import build_vector_store
from rag.retriever import get_retriever
from rag.prompt import RAG_PROMPT
from llm.gemini import get_llm


VECTOR_DB_PATH = Path("database/faiss_index")


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