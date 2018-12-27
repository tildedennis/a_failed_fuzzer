# http://www.w3schools.com/js/js_reserved.asp

import sys

import bs4
import requests


def parse_index(url):
    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    table = soup.find("table")
    for td in table.find_all("td"):
        content = td.text.strip().replace("*", "")
        if not content:
            continue

        print content


if __name__ == "__main__":
    parse_index(sys.argv[1])
