# https://developer.mozilla.org/en-US/docs/Web/HTML/Reference
#   https://developer.mozilla.org/en-US/docs/Web/HTML/Element HTML/Element
#   https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes HTML/Global_attributes

# https://developer.mozilla.org/en-US/docs/Web/CSS/Reference CSS
    
# https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference
#   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects JavaScript/Reference/Global_Objects
#   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators JavaScript/Reference/Operators
#   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements JavaScript/Reference/Statements
#   https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions JavaScript/Reference/Functions

# https://developer.mozilla.org/en-US/docs/Web/Reference/API
#   https://developer.mozilla.org/en-US/docs/Web/API API
#   https://developer.mozilla.org/en-US/docs/Web/Events Events

# https://developer.mozilla.org/en-US/docs/Web/SVG
#   https://developer.mozilla.org/en-US/docs/Web/SVG/Element SVG/Element
#   https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute SVG/Attribute

# https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API API

# https://developer.mozilla.org/en-US/docs/Web/MathML
#   https://developer.mozilla.org/en-US/docs/Web/MathML/Element MathML/Element

import re
import sys
import time

import bs4
import requests


def main(url, code_type, descend=False):
    print url
    filenames = parse_index(url, code_type)
    for i, filename in enumerate(filenames):
        print "%s (%d/%d)" % (filename, (i + 1), len(filenames))
        scrape(url, filename, descend) 
        time.sleep(1)


def parse_index(url, code_type):
    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    filenames = []
    for link in soup.find_all("a"):
        if "href" not in link.attrs:
            continue

        match = re.search(r'/en-US/docs/Web/%s/(?P<filename>[^"]+)' % code_type, link["href"])
        if match:
            filename = match.groupdict()["filename"]
            filenames.append(filename)

    return set(filenames)


def scrape(url, filename, descend=False):
    if "CSS/Reference" in url:
        url = url[:url.rfind("/Reference")] + "/%s" % filename
    else:
        url += "/%s" % filename

    match = re.search(r"/Web/(?P<filename>[^/]+/.*)", url)
    if not match:
        return

    new_filename = match.groupdict()["filename"]
    filename = new_filename.replace("/", "_")
    filename = filename.replace(":", "_")
    filename = filename.replace("*", "_")

    request = requests.get(url)
    soup = bs4.BeautifulSoup(request.content, "html.parser")

    examples = soup.find_all(class_="brush: html") + soup.find_all(class_="brush:html") + soup.find_all(class_="brush:css") + soup.find_all(class_="brush: css") + soup.find_all(class_="brush: js") + soup.find_all(class_="brush:js")
    for i, example in enumerate(examples):
        contents = example.getText()

        if "css" in " ".join(example["class"]) and "<html>" not in contents:
            contents = "<style>\n" + contents + "</style>"

        if "js" in " ".join(example["class"]) and "<html>" not in contents:
            contents = "<script>\n" + contents + "</script>"

        fp = open("../../corpus/mdn/%s%d" % (filename, i), "wb")
        try:
            fp.write(contents.encode("utf-8"))
        except Exception as err:
            print "couldn't write %s%d: %s" % (filename, i, err)

        fp.close()

    if descend:
        match = re.search(r"/en-US/docs/Web/(?P<code_type>.*)", url)
        if not match:
            return

        code_type = match.groupdict()["code_type"]
        main(url, code_type, False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], True)
