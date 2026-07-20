from utils.file_scanner import scan_folder
from loaders.loader_manager import load_document
from rag.chunking import split_documents


def main():

    print("=" * 60)
    print("LocalDocs AI Assistant")
    print("=" * 60)

    files = scan_folder("data")

    documents = []

    for file in files:

        try:

            document = load_document(file)

            if document:
                documents.append(document)
                print(f"✅ Loaded {file.name}")

        except Exception as e:

            print(f"❌ {file.name}")
            print(e)

    print("\nSplitting documents...\n")

    chunks = split_documents(documents)

    print(f"Created {len(chunks)} chunks.\n")

    for i, chunk in enumerate(chunks[:5]):

        print("-" * 60)

        print(f"Chunk {i+1}")

        print(chunk["filename"])

        print()

        print(chunk["content"][:250])

        print()

    print("...")



if __name__ == "__main__":
    main()