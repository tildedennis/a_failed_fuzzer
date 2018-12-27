# http://www.w3schools.com/html/default.asp html
# http://www.w3schools.com/css/default.asp css
# http://www.w3schools.com/js/default.asp js
# http://www.w3schools.com/canvas/default.asp canvas
# http://www.w3schools.com/svg/default.asp svg

# http://www.w3schools.com/tags/default.asp tags
# http://www.w3schools.com/tags/ref_eventattributes.asp tags
# http://www.w3schools.com/tags/ref_attributes.asp tags
# http://www.w3schools.com/cssref/default.asp cssref
# http://www.w3schools.com/cssref/css_selectors.asp cssref
# http://www.w3schools.com/jsref/default.asp jsref

import os
import re
import sys
import time

import bs4
import requests


def main(url, code_type):
    existing = os.listdir("../../corpus/w3schools/")

    filenames = parse_index(url, code_type)
    for filename in set(filenames):
        pages = parse_page(filename, code_type)
        for page in set(pages):
            if page in existing:
                continue

            print page
            scrape(page, code_type)

            time.sleep(0.5)


def parse_index(url, code_type):
    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    all_filenames = []
    filenames = []
    for link in soup.find_all("a"):
        if "href" not in link.attrs:
            continue

        match = re.search(r"(?P<filename>.*\.asp)", link["href"])
        if match:
            filename = match.groupdict()["filename"]
            if "/" in filename:
                continue

            filenames.append(filename)
            all_filenames.append(filename)

    if code_type == "jsref":
        for filename in set(filenames):
            url = "http://www.w3schools.com/%s/%s" % (code_type, filename)
            request = requests.get(url)
            soup = bs4.BeautifulSoup(request.content, "html.parser")

            for link in soup.find_all("a"):
                if "href" not in link.attrs:
                    continue

                match = re.search(r"(?P<filename>.*\.asp)", link["href"])
                if match:
                    filename = match.groupdict()["filename"]
                    if "/" in filename:
                        continue

                    all_filenames.append(filename)

            time.sleep(0.5)

    return all_filenames


def parse_page(index, code_type):
    url = "http://www.w3schools.com/%s/%s" % (code_type, index)
    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    filenames = []
    for link in soup.find_all("a"):
        if "href" not in link.attrs:
            continue

        match = re.search(r"tryit\.asp\?filename=(?P<filename>[\S]+)", link["href"])
        if match:
            filenames.append(match.groupdict()["filename"])

    return filenames


def scrape(page, code_type):
    url = "http://www.w3schools.com/%s/tryit.asp?filename=%s" % (code_type, page)
    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    example = soup.find(id="textareaCode")
    if not example:
        return

    contents = example.encode_contents()

    fp = open("../../corpus/w3schools/%s" % page, "wb")
    fp.write(contents)
    fp.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
