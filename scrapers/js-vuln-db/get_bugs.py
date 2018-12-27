# git clone https://github.com/tunz/js-vuln-db

import os
import sys 

file_num = 0 
for root, _, files in os.walk(sys.argv[1]):
    for file_name in files:
        if file_name.endswith(".js"):
            fp = open(os.path.join(root, file_name), "rb")
            contents = fp.read()
            fp.close()

            contents = "<script>\n" + contents + "\n</script>"

            fp = open("../../corpus/js-vuln-db/%d.html" % file_num, "wb")
            fp.write(contents)
            fp.close()

            file_num += 1
