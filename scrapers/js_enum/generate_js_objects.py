# python generate_js_objects.py js_objects > js_objects.html

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
    var items = [%s];
    for (i = 0; i < items.length; i++) {
        try {
            var oObject = eval(items[i]);
        } catch(e) {
            continue;
        }

        for (var property in oObject) {
            try {
                var oProperty = oObject[property];
            } catch(e) {
                continue;
            }

            if (typeof oProperty === 'function')
                document.write(items[i] + ',method,' + property + '\\n');
            else
                document.write(items[i] + ',property,' + property + '\\n');
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
    fp = open(sys.argv[1], "rb")
    content = fp.readlines()
    fp.close()

    items = [i.strip() for i in content]
    print generate_js(items)
