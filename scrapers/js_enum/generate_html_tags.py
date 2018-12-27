# python generate_html_tags.py ../../pieces/html_tags ../manual/manual_tags > html_tags.html

import json
import sys


def generate_js(items):
    item_str = ""
    for item in items:
        item_str += "'%s'," % str(item)

    item_str = item_str.rstrip(",")

    template = """
    <html>
    <head>
    <script>
    var elements = [%s];
    for (i = 0; i < elements.length; i++) {
        var oElement = document.createElement(elements[i])

        for (var property in oElement) {
            var oProperty = oElement[property]

            if (typeof oProperty === 'function')
                document.write("document.createElement('" + elements[i] + "')" + ',method,' + property + '\\n');
            else
                document.write("document.createElement('" + elements[i] + "')" + ',property,' + property + '\\n');
        }
    }
    </script>
    </head>
    <body>
    </body>
    </html>
    """ % item_str

    return template


if __name__ == "__main__":
    items = {}

    for filename in sys.argv[1:]:
        fp = open(filename, "rb")
        content = fp.read()
        fp.close()

        items.update(json.loads(content))

    print generate_js(items.keys())
