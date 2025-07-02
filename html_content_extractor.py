from bs4 import BeautifulSoup, Comment


def extract_clean_content(html_content):
    """
    HTMLから不要なタグを削除するだけのシンプル版（有用なHTMLタグは保持）
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # 不要なタグを完全に削除
    unwanted_tags = [
        "script",
        "style",
        "meta",
        "link",
        "noscript",
        "iframe",
        "embed",
        "object",
        "form",
        "input",
        "button",
        "select",
        "textarea",
        "nav",
        "header",
        "footer",
        "aside",
        "advertisement",
    ]

    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    # HTMLコメントを削除
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # 残ったHTMLをそのまま返す（タグ付きで）
    return str(soup)
