# https://msdn.microsoft.com/en-us/library/hh772374(v=vs.85).aspx

import json
import re
import sys
import time

import bs4
import requests


def main(index_url, code_type):
    filenames = parse_index(index_url, code_type)
    for i, filename in enumerate(filenames):
        print "%d/%d files" % ((i + 1), len(filenames))
        scrape(base_url, filename, True)
        
        fp = open("visited.json", "w")
        fp.write(json.dumps(visited))
        fp.close()


def parse_index(url, code_type):
    time.sleep(1)
    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    filenames = []
    for td in soup.find_all("td", {"data-th": code_type}):
        for link in td.find_all("a"):
            if "href" not in link.attrs:
                continue

            match = re.search(r'https://msdn.microsoft.com/en-us/library/(?P<filename>.*\.aspx)', link["href"])
            if match:
                filename = match.groupdict()["filename"]
                filenames.append(filename)

    return set(filenames)


def scrape(url, filename, descend=False):
    if filename in visited:
        return

    print "scraping %s" % filename
    visited.append(filename)

    url += "/%s" % filename

    time.sleep(1)
    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    examples = soup.find_all(class_="codeSnippetContainerCode")
    for i, example in enumerate(examples):
        contents = example.getText().strip()

        if example.parent.parent.find(text="JavaScript"):
            print "JavaScript"
            # some JavaScript examples are actually HTML
            if not contents.startswith("<") and not contents.startswith("..."):
                contents = "<script>\n" + contents + "\n</script>"

        elif example.parent.parent.find(text="HTML"):
            print "HTML"

        elif example.parent.parent.find(text="CSS"):
            print "CSS"
            if not contents.startswith("<style"):
                contents = "<style>\n" + contents + "\n</style>"

        else:
            continue

        print contents

        fp = open("../../corpus/msdn/%s%d" % (filename, i), "wb")
        try:
            fp.write(contents.encode("utf-8"))
        except Exception as err:
            print "couldn't write %s%d: %s" % (filename, i, err)

        fp.close()

    if descend:
        descendants = soup.find_all("td", {"data-th": "Event"}) + soup.find_all("td", {"data-th": "Method"}) + soup.find_all("td", {"data-th": "Property"})
        for i, td in enumerate(set(descendants)):
            print "%d/%d descendants" % ((i + 1), len(descendants))
            for link in td.find_all("a"):
                if "href" not in link.attrs:
                    continue

                match = re.search(r'https://msdn.microsoft.com/en-us/library/(?P<filename>.*\.aspx)', link["href"])
                if match:
                    filename = match.groupdict()["filename"]
                    scrape(base_url, filename, False)


if __name__ == "__main__":
    base_url = "https://msdn.microsoft.com/en-us/library/"

    try:
        fp = open("visited.json", "r")
        data = fp.read()
        visited = json.loads(data)
        fp.close()
    except:
        visited = []

    main(sys.argv[1], sys.argv[2])
