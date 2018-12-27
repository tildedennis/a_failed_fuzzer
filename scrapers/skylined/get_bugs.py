# git clone https://github.com/SkyLined/Bugs.git

import os
import sys 

file_num = 0 
for root, _, files in os.walk(sys.argv[1]):
    for file_name in files:
        if file_name.startswith("repro") and file_name.endswith(".html"):
            fp = open(os.path.join(root, file_name), "rb")
            contents = fp.read()
            fp.close()

            fp = open("../../corpus/skylined/%d.html" % file_num, "wb")
            fp.write(contents)
            fp.close()

            file_num += 1
