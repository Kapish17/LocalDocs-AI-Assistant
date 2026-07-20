from utils.file_scanner import scan_folder


def main():

    print("=" * 60)
    print("LocalDocs AI Assistant")
    print("=" * 60)

    files = scan_folder("data")

    print("\nSupported Files\n")

    if not files:
        print("No supported files found.")
        return

    for file in files:
        print(file.name)


if __name__ == "__main__":
    main()