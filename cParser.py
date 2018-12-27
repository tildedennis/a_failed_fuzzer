import json
import logging
import os
import re

import bs4


class cParser:

    JS_IDENTIFIER = "[a-zA-Z_$][a-zA-Z0-9_$]*"


    def __init__(self):
        self.html_tags = {}
        self.html_events = []
        self.html_attributes = {}

        self.css_selector_gadgets = []
        self.css_declarations = {}
        self.css_functions = {}

        self.js_objects = {}
        self.js_gadgets = []


    def parse_corpus(self):
        has_pieces = self.load_pieces()

        if not has_pieces:
            num_files = 0

            for root, _, files in os.walk("corpus"):
                for file_name in files:
                    fp = open(os.path.join(root, file_name), "rb")
                    file_content = fp.read()
                    fp.close()

                    self.parse_content(file_content)
                    num_files += 1

            logging.info("parsed %d files from corpus", num_files)

        # replace css selector html tags after all html tags have been parsed
        self.css_selector_gadgets = self.replace_css_selector_tags()

        # parse all html attributes
        self.html_attributes = self.parse_html_attributes()

        logging.info("parsed %d html tags", len(self.html_tags))
        logging.info("parsed %d html attributes", len(self.html_attributes))
        logging.info("parsed %d css selector gadgets", len(self.css_selector_gadgets))
        logging.info("parsed %d css declarations", len(self.css_declarations))
        logging.info("parsed %d css functions", len(self.css_functions))
        logging.info("parsed %d js gadgets", len(self.js_gadgets))


    def parse_content(self, content):
        # skip XML examples
        if content.startswith("<?xml"):
            return

        soup = bs4.BeautifulSoup(content, "html.parser")

        identifiers = []
        object_mappings = []
        for element in soup.find_all(True):
            # html
            identifiers = self.parse_html(element, identifiers)

            # css
            if element.name == "style":
                identifiers = self.parse_css(element.string, identifiers)

            if "style" in element.attrs:
                identifiers = self.parse_css(element["style"], identifiers)

            # js identifiers
            if element.name == "script":
                identifiers, object_mappings = self.parse_js_identifiers(element.string, identifiers, object_mappings)

            events = [e for e in self.html_events if element.has_attr(e)]
            for event in events:
                identifiers, object_mappings = self.parse_js_identifiers(element[event], identifiers, object_mappings)

        # js
        for element in soup.find_all(True):
            if element.name == "script":
                self.parse_and_replace_js(element.string, identifiers, object_mappings)

            events = [e for e in self.html_events if element.has_attr(e)]
            for event in events:
                self.parse_and_replace_js(element[event], identifiers, object_mappings)


    def parse_html(self, element, identifiers):
        # tag name
        try:
            tag_name = str(element.name.strip())
        except UnicodeEncodeError:
            return identifiers

        # remove cruft
        if re.search(r"(\"|,|;)", tag_name):
            return identifiers

        tag = self.html_tags.get(tag_name, {})

        # attributes
        for attr_name, attr_values in element.attrs.iteritems():
            # attr name
            try:
                attr_name = str(attr_name.strip())
            except UnicodeEncodeError:
                continue

            # remove cruft
            if not attr_name:
                continue

            if re.search(r"(\"|,|;|\(|\)|\.|<)", attr_name):
                continue

            # replace identifiers
            if attr_name.startswith("data-"):
                if attr_name not in identifiers:
                    identifiers.append(attr_name)
                attr_name = "data-$FI_IDENTIFIER"

            # events
            if attr_name.startswith("on") and attr_name not in self.html_events:
                self.html_events.append(attr_name)

            if attr_name not in tag:
                tag[attr_name] = []

            # attr values
            if type(attr_values) is not list:
                attr_values = [attr_values]

            for attr_value in attr_values:
                try:
                    attr_value = str(attr_value.strip())
                except UnicodeEncodeError:
                    continue

                # remove cruft
                if not attr_value:
                    continue

                attr_value = attr_value.replace("\n", "")

                # event values are generated
                if attr_name in self.html_events:
                    continue

                # style values are generated
                if attr_name == "style":
                    continue

                # normalize quotes
                attr_value = attr_value.replace('"', "'")

                # replace identifiers
                if attr_name in ["usemap", "id", "class", "name", "form", "for"]:
                    if attr_value not in identifiers:
                        identifiers.append(attr_value)
                    attr_value = "$FI_IDENTIFIER"

                if attr_name == "target" and not attr_value.startswith("_"):
                    if attr_value not in identifiers:
                        identifiers.append(attr_value)
                    attr_value = "$FI_IDENTIFIER"

                # css function
                if self.parse_css_function_call(attr_value):
                    attr_value = "$FI_CSS_FUNCTION"

                if attr_value not in tag[attr_name]:
                    tag[attr_name].append(attr_value)

        self.html_tags.update({tag_name: tag})

        return identifiers


    def parse_html_attributes(self):
        all_attribs = {}

        for _, attribs in self.html_tags.iteritems():
            for name, values in attribs.iteritems():
                if name not in all_attribs:
                    all_attribs[name] = []

                for value in values:
                    if value not in all_attribs[name]:
                        all_attribs[name].append(value)

        return all_attribs


    def parse_css(self, content, identifiers):
        if not content:
            return identifiers

        for line in content.splitlines():
            try:
                line = str(line.strip())
            except UnicodeEncodeError:
                continue

            # remove cruft
            if not line:
                continue

            # normalize quotes
            line = line.replace('"', "'")

            identifiers = self.parse_css_selector(line, identifiers)
            self.parse_css_declaration(line)

        return identifiers


    def parse_css_selector(self, line, identifiers):
        match = re.search(r"(?P<selectors>[^{]+)\s*{", line)
        if not match:
            return identifiers

        selectors = match.groupdict()["selectors"]

        # comma separated
        for selector in selectors.split(","):
            selector = str(selector.strip())

            # remove cruft
            if not selector:
                continue

            # replace identifiers
            # #id
            # .class
            id_matches = re.finditer(r"(#|\.)(?P<identifier>[a-zA-Z0-9_-]+)", selector)
            for id_match in id_matches:
                identifier = str(id_match.groupdict()["identifier"].strip())
                if identifier not in identifiers:
                    identifiers.append(identifier)
                selector = re.sub(re.escape(identifier), "$FI_IDENTIFIER", selector)

            # @keyframes
            kf_match = re.search(r"@[\S]*keyframes\s+(?P<identifier>[a-zA-Z0-9_-]+)", selector)
            if kf_match:
                identifier = str(kf_match.groupdict()["identifier"].strip())
                if identifier not in identifiers:
                    identifiers.append(identifier)
                selector = re.sub(re.escape(identifier), "$FI_IDENTIFIER", selector)

            # [class]
            attr_match = re.search(r"\[class\s*[~|\^$*]?=\s*'?(?P<identifier>[a-zA-Z0-9_-]+)'?\]", selector)
            if attr_match:
                identifier = str(attr_match.groupdict()["identifier"].strip())
                if identifier not in identifiers:
                    identifiers.append(identifier)
                selector = re.sub(re.escape(identifier), "$FI_IDENTIFIER", selector)

            if selector not in self.css_selector_gadgets:
                self.css_selector_gadgets.append(selector)

        return identifiers


    def replace_css_selector_tags(self):
        tags = "(" + "|".join(self.html_tags) + ")"
        updated = []

        for selector in self.css_selector_gadgets:
            selector = re.sub(r"\b%s\b" % tags, "$FI_TAG", selector)
            if selector not in updated:
                updated.append(selector)

        return updated


    def parse_css_declaration(self, line):
        matches = re.finditer(r"(?P<name>[a-zA-Z0-9_-]+)\s*:\s*(?P<value>[^;]+);", line)
        for match in matches:
            # property name
            name = str(match.groupdict()["name"].strip())

            declaration = self.css_declarations.get(name, [])

            # property value
            value = str(match.groupdict()["value"].strip())

            # remove cruft
            if not value:
                continue

            # css function
            if self.parse_css_function_call(line):
                value = "$FI_CSS_FUNCTION"

            if value not in declaration:
                declaration.append(value)

            self.css_declarations.update({name: declaration}) 


    def parse_css_function_call(self, line):
        match = re.search(r"(?P<name>[a-zA-Z_\.-]+)\s*\((?P<args>[^\)]*)\)", line)
        if not match:
            return False

        # function name
        name = str(match.groupdict()["name"].strip())

        # remove cruft
        if name == "-":
            return False

        function = self.css_functions.get(name, [])

        # function arguments
        args = str(match.groupdict()["args"].strip())

        # remove cruft
        if "..." in args:
            return False

        # map for no arguments
        if not args:
            args = ""

        if args not in function:
            function.append(args)

        self.css_functions.update({name: function})

        return True


    def parse_js_identifiers(self, content, identifiers, object_mappings):
        if not content:
            return identifiers, object_mappings

        for line in content.splitlines():
            try:
                line = str(line.strip())
            except UnicodeEncodeError:
                continue

            # remove cruft
            # comments
            if line.startswith("//"):
                continue

            line = re.sub(r"//.*$", "", line)
            line = re.sub(r"/\*.*\*/", "", line)
            line = re.sub(r"/\*.*$", "", line)

            if "..." in line:
                continue

            if not line:
                continue

            # normalize quotes
            line = line.replace('"', "'")

            # misc identifiers
            misc_identifiers = self.parse_js_misc_identifiers(line)
            for misc_identifier in misc_identifiers:
                if misc_identifier not in identifiers:
                    identifiers.append(misc_identifier)

            # function definition
            identifiers = self.parse_js_function_definition(line, identifiers)

            # object mappings
            object_mappings = self.parse_js_object_mappings(line, object_mappings)

        return identifiers, object_mappings


    def parse_js_misc_identifiers(self, line):
        identifiers = []

        regexes = [
            # var identifier
            r"var\s+(?P<identifier>%s)" % self.JS_IDENTIFIER,

            # identifier =
            r"(?P<identifier>%s)\s*=[^=]" % self.JS_IDENTIFIER,

            # = identifier;
            r"=\s*(?P<identifier>%s);" % self.JS_IDENTIFIER,

            # identifier:
            r"\b(?P<identifier>%s):" % self.JS_IDENTIFIER,

            # class identifier {
            r"class (?P<identifier>%s)[^\{]+\{" % self.JS_IDENTIFIER,

            # extends identifier {
            r"extends (?P<identifier>%s)[^\{]+\{" % self.JS_IDENTIFIER,

            # identifier[
            r"(?P<identifier>%s)\[" % self.JS_IDENTIFIER
        ]

        for regex in regexes:
            matches = re.finditer(regex, line)
            for match in matches:
                identifier = str(match.groupdict()["identifier"].strip())

                # remove cruft
                if identifier in self.js_reserved_words:
                    continue

                if identifier in ["http", "https"]:
                    continue

                if identifier not in identifiers:
                    identifiers.append(identifier)

        return identifiers


    def parse_js_function_definition(self, line, identifiers):
        regexes = [
            # function identifier(args)
            r"function\s+(?P<name>%s)\s*\((?P<args>[^\)]*)\)" % self.JS_IDENTIFIER,

            # function(args)
            r"(?P<name>function)\s*\((?P<args>[^\)]*)\)",

            # catch(args)
            r"(?P<name>catch)\s*\((?P<args>[^\)]*)\)"
        ]

        for regex in regexes:
            match = re.search(regex, line)
            if not match:
                continue

            # function name
            name = str(match.groupdict()["name"].strip())

            if name not in ["function", "catch"]:
                if name not in identifiers:
                    identifiers.append(name)

            # function arguments
            args = str(match.groupdict()["args"].strip())
            for arg in args.split(","):
                arg = str(arg.strip())

                # remove cruft
                if re.match(r"^[a-zA-Z0-9_$]+$", arg):
                    if arg not in identifiers:
                        identifiers.append(arg)

        return identifiers


    def parse_js_object_mappings(self, line, object_mappings):
        regexes = [
            # document.createElement
            r"(?P<name>%s)\s*=\s*document\.createElement\('(?P<tag>[^\)]+)'\)" % self.JS_IDENTIFIER,

            # new Object
            r"(?P<name>%s)\s*=\s*new\s+(?P<object>%s)" % (self.JS_IDENTIFIER, self.JS_IDENTIFIER)
        ]

        for regex in regexes:
            matches = re.finditer(regex, line)
            for match in matches:
                name = match.groupdict()["name"]

                if "tag" in match.groupdict():
                    tag = match.groupdict()["tag"]
                    obj = "document.createElement('%s')" % tag.lower()
                else:
                    obj = match.groupdict()["object"]

                object_mappings.append({"name": name, "object": obj})

        return object_mappings


    def parse_and_replace_js(self, content, identifiers, object_mappings):
        if not content:
            return

        for line in content.splitlines():
            try:
                line = str(line.strip())
            except UnicodeEncodeError:
                continue

            # remove cruft
            # comments
            if line.startswith("//"):
                continue

            line = re.sub(r"//.*$", "", line)
            line = re.sub(r"/\*.*\*/", "", line)
            line = re.sub(r"/\*.*$", "", line)

            if "..." in line:
                continue

            if not line:
                continue

            # normalize quotes
            line = line.replace('"', "'")

            # order matters

            # objects
            objects = self.parse_js_objects(line, object_mappings)
            for obj in objects:
                line = re.sub(r"\b%s" % re.escape(obj), "$FI_JS_OBJECT.", line)

            # new objects
            objects = self.parse_js_new_objects(line)
            for obj in objects:
                line = re.sub(r"%s\([^\)]*\)" % re.escape(obj), "$FI_JS_OBJECT", line)

            # methods
            methods = self.parse_js_methods(line)
            for method in methods:
                line = re.sub(r"\.%s\([^\)]*\)" % re.escape(method["name"]), ".$FI_JS_METHOD", line)

            # properties
            properties = self.parse_js_properties(line)
            for obj_property in properties:
                line = re.sub(r"\.%s" % re.escape(obj_property), ".$FI_JS_PROPERTY", line)

            # function calls
            calls = self.parse_js_function_calls(line, object_mappings)
            for call in calls:
                line = re.sub(r"%s\([^\)]*\)" % re.escape(call), "$FI_JS_FUNCTION", line)

            # identifiers
            for identifier in identifiers:
                line = re.sub(r"\b%s\b" % re.escape(identifier), "$FI_IDENTIFIER", line)

            # literals
            literals = self.parse_js_literals(line)
            for literal in literals:
                line = re.sub(r"%s" % re.escape(literal), "$FI_JS_LITERAL", line)

            if line not in self.js_gadgets:
                self.js_gadgets.append(line)


    def parse_js_literals(self, line):
        literals = []

        regexes = [
            # operator hex number
            r"%s\s*(?P<literal>0[xX][0-9a-fA-F]+)" % ("(" + "|".join(self.js_operators) + ")"),

            # hex number,)];:}
            r"(?P<literal>0[xX][0-9a-fA-F]+)[,\)\];:\}]",

            # ([hex number
            r"[\(\[](?P<literal>0[xX][0-9a-fA-F]+)",

            # operator decimal number
            r"%s\s*(?P<literal>(\-)?[0-9]([0-9\.]+)?)" % ("(" + "|".join(self.js_operators) + ")"),

            # decimal number,)];:}
            r"(?P<literal>(\-)?[0-9]([0-9\.]+)?)[,\)\];:\}]",

            # ([decimal number
            r"[\(\[](?P<literal>(\-)?[0-9]([0-9\.]+)?)",

            # operator string
            r"%s\s*(?P<literal>'[^']+')" % ("(" + "|".join(self.js_operators) + ")"),

            # string,)];:}
            r"(?P<literal>'[^']+')[,\)\];:\}]",

            # ([string
            r"[\(\[](?P<literal>'[^']+')"
        ]

        for regex in regexes:
            matches = re.finditer(regex, line)
            for match in matches:
                literal = str(match.groupdict()["literal"].strip())

                # remove cruft
                if not literal:
                    continue

                if literal not in literals:
                    literals.append(literal)

        return literals


    def parse_js_methods(self, line, obj=None):
        methods = []

        if obj:
            matches = re.finditer(r"%s\.(?P<name>%s)\s*\((?P<args>[^\)]*)\)" % (obj, self.JS_IDENTIFIER), line)
        else:
            matches = re.finditer(r"\.(?P<name>%s)\s*\((?P<args>[^\)]*)\)" % self.JS_IDENTIFIER, line)

        for match in matches:
            method = str(match.groupdict()["name"].strip())
            args = str(match.groupdict()["args"].strip())

            methods.append({"name": method, "args": args})

        return methods


    def parse_js_properties(self, line, obj=None):
        properties = []

        if obj:
            matches = re.finditer(r"%s\.(?P<name>%s)(?P<bracket>\()?" % (obj, self.JS_IDENTIFIER), line)
        else:
            matches = re.finditer(r"\.(?P<name>%s)(?P<bracket>\()?" % self.JS_IDENTIFIER, line)

        for match in matches:
            obj_property = str(match.groupdict()["name"].strip())

            # remove cruft
            # already a method
            if obj_property == "$FI_JS_METHOD":
                continue

            if match.groupdict()["bracket"]:
                continue

            if obj_property not in properties:
                properties.append(obj_property)

        return properties


    def parse_js_objects(self, line, object_mappings):
        objects = []

        regexes = [
            # object.
            r"(?P<name>(%s\.)+)" % self.JS_IDENTIFIER,

            # instanceof object
            r"instanceof\s+(?P<name>%s)" % self.JS_IDENTIFIER
        ]

        for regex in regexes:
            matches = re.finditer(regex, line)
            for match in matches:
                obj = str(match.groupdict()["name"].strip())

                if obj not in objects:
                    objects.append(obj)

                # update global js objects
                if obj.endswith("."):
                    real_obj = obj[:-1]
                else:
                    real_obj = obj

                # get methods/properties before mapping
                methods = self.parse_js_methods(line, real_obj)
                properties = self.parse_js_properties(line, real_obj)

                # map object name to object
                for object_mapping in object_mappings:
                    if real_obj == object_mapping["name"]:
                        real_obj = object_mapping["object"]
                        break

                js_object = self.js_objects.get(real_obj, {})
                if not js_object:
                    continue

                for obj_property in properties:
                    if obj_property not in js_object["properties"]:
                        js_object["properties"].append(obj_property)

                for method in methods:
                    if method["name"] in js_object["methods"]:
                        js_object["methods"][method["name"]].append(method["args"])
                    else:
                        js_object["methods"].update({method["name"]: []})
                        js_object["methods"][method["name"]].append(method["args"])

                self.js_objects.update({real_obj: js_object})

        return objects


    def parse_js_new_objects(self, line):
        objects = []

        matches = re.finditer(r"new\s+(?P<name>%s)\s*\(" % self.JS_IDENTIFIER, line)
        for match in matches:
            obj = str(match.groupdict()["name"].strip())

            if obj not in objects:
                objects.append(obj)

        return objects


    def parse_js_function_calls(self, line, object_mappings):
        calls = []

        matches = re.finditer(r"(?P<name>%s)\s*\((?P<args>[^\)]*)\)" % self.JS_IDENTIFIER, line)
        for match in matches:
            name = str(match.groupdict()["name"].strip())
            args = str(match.groupdict()["args"].strip())

            # remove cruft
            # reserved words
            if name in self.js_reserved_words:
                continue

            # methods
            if ".%s" % name in line:
                continue

            # constructors
            found = False
            for object_mapping in object_mappings:
                if name == object_mapping["object"]:
                    found = True
                    break

            if found:
                continue

            if name not in calls:
                calls.append(name)

            # update global js objects
            window_object = self.js_objects.get("window")
            if name in window_object["methods"]:
                window_object["properties"].append(args)
                self.js_objects.update({"window": window_object})

        return calls


    def read_dict_js_objects(self, path):
        lines = self.read_dict(path)
        for line in lines:
            obj_name, property_type, obj_property = line.split(",")

            obj = self.js_objects.get(obj_name, {})
            if not obj:
                obj = {
                    "properties": [],
                    "methods": {}
            }

            if property_type == "method":
                obj["methods"].update({obj_property: []})
            else:
                obj["properties"].append(obj_property)
                
            self.js_objects.update({obj_name: obj})


    def read_dicts(self):
        self.html_events = self.read_dict("dicts/html_events")
        self.js_reserved_words = self.read_dict("dicts/js_reserved_words")
        self.js_operators = self.read_dict("dicts/js_operators")
        self.read_dict_js_objects("dicts/js_objects")

        logging.info("read %d html events", len(self.html_events))
        logging.info("read %d js reserved words", len(self.js_reserved_words))
        logging.info("read %d js operators", len(self.js_operators))
        logging.info("read %d js objects", len(self.js_objects))


    @staticmethod
    def read_dict(path):
        fp = open(path, "r")
        lines = fp.readlines()
        fp.close()

        lines = [line.strip() for line in lines if not line.startswith("#")]

        return lines


    def load_pieces(self):
        for piece in [p for p in dir(self) if re.match("^(html|css|js)_", p)]:
            try:
                fp = open("pieces/%s" % piece, "r")
            except IOError:
                continue

            value = json.loads(fp.read())
            fp.close()
            setattr(self, piece, value)

        for piece in [p for p in dir(self) if re.match("^(html|css|js)_", p)]:
            if not getattr(self, piece):
                return False

        logging.info("using cached pieces")

        return True
