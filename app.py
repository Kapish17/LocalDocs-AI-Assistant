from utils.file_scanner import scan_folder
from loaders.loader_manager import load_document
from rag.chunking import split_documents
from rag.vector_store import create_vector_store


def main():

    print("=" * 60)
    print("LocalDocs AI Assistant")
    print("=" * 60)

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
            print(f"Error: {e}")

    print("\nSplitting documents...\n")

    chunks = split_documents(documents)

    print("=" * 60)
    print("Chunking Complete")
    print("=" * 60)

    print(f"📄 Total Documents : {len(documents)}")
    print(f"🧩 Total Chunks    : {len(chunks)}")

    print("\nFirst 3 Chunks Preview\n")

    for i, chunk in enumerate(chunks[:3], start=1):
        print("-" * 60)
        print(f"Chunk {i}")
        print(f"Source : {chunk.metadata['source']}")
        print(f"Type   : {chunk.metadata['file_type']}")
        print(chunk.page_content[:300])
        print()

    # Create FAISS Vector Store
    print("=" * 60)
    print("Creating Vector Store")
    print("=" * 60)

    vector_store = create_vector_store(chunks)

    print("\n✅ FAISS Vector Store Created Successfully!")
    print("📂 Saved in: database/faiss_index/")


if __name__ == "__main__":
    main()