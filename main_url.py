import search_subsidy
import page_classifier


def main():
    prefecture = search_subsidy.main()
    page_classifier.main(prefecture)


if __name__ == "__main__":
    main()
