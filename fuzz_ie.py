import argparse
import datetime
import json
import logging
import os
import re
import shutil
import threading
import time

try:
    from cBugId import cBugId
except:
    pass

from cParser import cParser
from cGenerator import cGenerator
from http_server import HTTPServer


class Harness:

    def __init__(self, fuzz, pieces):
        self.start_time = time.time()
        self.init_logging()

        oParser = cParser()
        oParser.read_dicts()
        oParser.parse_corpus()

        if pieces:
            self.dump_pieces(oParser)

        self.oGenerator = cGenerator(oParser)

        if not fuzz:
            return

        self.iexplore_path = "C:\\Program Files\\Internet Explorer\\iexplore.exe"
        self.url = self.start_http_server(4444)

        self.crashes = 0
        self.test_case_number = 0

        logging.info("startup time: %d seconds", (time.time() - self.start_time))


    def generate_test_case(self):
        test_case = self.oGenerator.generate()

        return test_case


    def fuzz(self):
        while True:
            logging.info("-"*32)
            logging.info("%d crashes", self.crashes)

            elapsed_time = time.time() - self.start_time
            logging.info("elapsed time: %s", str(datetime.timedelta(seconds=elapsed_time)))

            speed = float(self.test_case_number) / (float(elapsed_time) / 60.0 / 60.0)
            logging.info("%d test cases/hour", speed)

            self.test_case_number += 1
            logging.info("test case %d", self.test_case_number)

            test_case = self.generate_test_case()
            logging.info(test_case)
            self.write_test_case(test_case)

            command_line = [self.iexplore_path, self.url]

            oBugId = cBugId(
                asApplicationCommandLine = command_line,
                bGenerateReportHTML = True
            )

            oBugId.fStart()
            time.sleep(7)
            oBugId.fStop()

            if oBugId.oBugReport:
                self.save_crash(oBugId.oBugReport)


    @staticmethod
    def init_logging():
        fmt = "[%(levelname)s] %(asctime)s: %(message)s"
        datefmt = "%Y-%m-%d %I:%M:%S"

        logging.basicConfig(level=logging.INFO, filename="log", format=fmt, datefmt=datefmt)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        logging.getLogger("").addHandler(console)

        logging.info("-"*32)
        logging.info("log opened")


    @staticmethod
    def start_http_server(port):
        http_server_event = threading.Event()
        http_server = HTTPServer(port, http_server_event)
        http_server.daemon = True
        http_server.start()
        http_server_event.wait()

        url = "http://localhost:%d/test_case/test_case.html" % port

        return url


    @staticmethod
    def write_test_case(test_case):
        # @DEBUG
        #fp = open("corpus/test/32.html", "rb")
        #test_case = fp.read()
        #fp.close()

        fp = open("test_case/test_case.html", "wb")
        try:
            fp.write(test_case)
        except UnicodeEncodeError:
            logging.warn("couldn't write test case")
            fp.write("")

        fp.close()


    def save_crash(self, oBugReport):
        self.crashes += 1

        logging.info("Id: %s" % oBugReport.sId)
        logging.info("Description: %s" % oBugReport.sBugDescription)
        logging.info("Location: %s" % oBugReport.sBugLocation)
        logging.info("Security impact: %s" % oBugReport.sSecurityImpact)

        date = datetime.datetime.now().strftime("%Y-%m-%d")
        if date not in os.listdir("crashes"):
            os.mkdir("crashes/%s" % date)

        if "crash_%d" % self.test_case_number not in os.listdir("crashes/%s" % date):
            os.mkdir("crashes/%s/crash_%d" % (date, self.test_case_number))

        fp = open("crashes/%s/crash_%d/report.html" % (date, self.test_case_number), "w")
        fp.write(oBugReport.sReportHTML)
        fp.close()

        shutil.copy("test_case/test_case.html", "crashes/%s/crash_%d/test_case.html" %
            (date, self.test_case_number))


    @staticmethod
    def dump_pieces(oParser):
        for piece in [p for p in dir(oParser) if re.match("^(html|css|js)_", p)]:
            fp = open("pieces/%s" % piece, "w")
            value = getattr(oParser, piece)
            fp.write(json.dumps(value))
            fp.close()

        logging.info("pieces dumped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fuzz", action="store_true")
    parser.add_argument("-p", "--pieces", action="store_true")
    args = parser.parse_args()

    harness = Harness(args.fuzz, args.pieces)

    if args.fuzz:
        harness.fuzz()
    else:
        print harness.generate_test_case()
