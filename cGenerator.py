import datetime
import logging
import random
import re


class cGenerator:

    MAX_HTML_TAGS = 3 
    MAX_HTML_ATTRIBUTES = 2
    MAX_CSS_RULES = 1
    MAX_CSS_DECLARATIONS = 2
    MAX_JS_GADGETS = 3
    MAX_JS_METHOD_ARGS = 4


    def __init__(self, dictionaries):
        self.dictionaries = dictionaries
        self.fuzz_values = self.init_fuzz_values()
        self.identifiers = ["x", "y", "this"]

        logging.info("%d fuzz values", len(self.fuzz_values))
        logging.info("%d identifiers", len(self.identifiers))


    def generate(self):
        # template based on https://www.blackhat.com/docs/eu-14/materials/eu-14-Lu-The-Power-Of-Pair-One-Template-That-Reveals-100-plus-UAF-IE-Vulnerabilities.pdf page 6
        test_case = []

        # tags part 1
        tags = []
        existing_tags = []
        for t in range(random.randint(1, self.MAX_HTML_TAGS)):
            tag = "<"

            # make end tags rare
            if self.onein(50):
                tag += "/"

            tag_name, tag_attributes = self.generate_html_tag()

            while tag_name in ["style", "script", "body"]:
                tag_name, tag_attributes = self.generate_html_tag()

            tag += tag_name

            if tag_name != "style" and tag_name not in existing_tags:
                existing_tags.append(tag_name)

            existing_attributes = []
            for a in range(random.randint(0, self.MAX_HTML_ATTRIBUTES)):
                attribute_name, attribute_value = self.generate_html_attribute(tag_attributes, existing_attributes)

                if attribute_name not in existing_attributes:
                    existing_attributes.append(attribute_name)

                if attribute_name == "style":
                    declarations = self.generate_css_declarations()
                    attribute_value = " ".join(declarations)

                if attribute_name in self.dictionaries.html_events:
                    attribute_value = "fuzz();"

                tag += ' %s="%s"' % (attribute_name, attribute_value)
            
            # make void tags rare
            if self.onein(50):
                tag += " /"

            tag += ">"

            tags.append(tag)

        # css
        css = "<style>\n"
        rules = self.generate_css(existing_tags)
        css += "\n".join(rules)
        css += "\n</style>"
        test_case.append(css)

        # script
        script = "<script>\n"
        script += self.generate_js(existing_tags)
        script += "\n</script>"
        test_case.append(script)

        # add some asynchronous execution
        timeout = random.randint(0, 7) * 1000
        script = "<script>setInterval(fuzz, %d);</script>" % timeout
        test_case.append(script)

        # tags part 2
        tag = '<body onload="fuzz();">'
        test_case.append(tag)

        test_case += tags
        tag = "</body>"
        test_case.append(tag)

        test_case = "\n".join(test_case)

        return test_case


    def generate_html_tag(self):
        tag = random.choice(self.dictionaries.html_tags.keys())
        attributes = self.dictionaries.html_tags[tag]

        return tag, attributes


    def generate_html_attribute(self, real_attributes, existing_attributes):
        not_found = True

        while not_found:
            # default to none
            value = ""

            # real attribute
            if self.morelikely() and real_attributes:
                name = random.choice(real_attributes.keys())

                if real_attributes[name]:
                    value = self.close_brackets(random.choice(real_attributes[name]))

            # random attribute
            else:
                name = random.choice(self.dictionaries.html_attributes.keys())

                if self.dictionaries.html_attributes[name]:
                    value = self.close_brackets(random.choice(self.dictionaries.html_attributes[name]))

            if name not in existing_attributes:
                not_found = False

            # identifiers
            while "$FI_IDENTIFIER" in value:
                value = re.sub(r"\$FI_IDENTIFIER", random.choice(self.identifiers), value, 1)

            # css function
            while "$FI_CSS_FUNCTION" in value:
                value = self.generate_css_function()

            if not value and self.morelikely():
                # fuzz value
                value = random.choice(self.fuzz_values)

        return name, value


    def generate_css_function(self):
        name = random.choice(self.dictionaries.css_functions.keys())
        if self.dictionaries.css_functions[name]:
            args = random.choice(self.dictionaries.css_functions[name])
        else:
            args = ""

        function = "%s(%s)" % (name, args)

        return function


    def generate_css_declarations(self):
        declarations = []

        for d in range(random.randint(1, self.MAX_CSS_DECLARATIONS)):
            # default to none
            value = ""

            declaration_property = random.choice(self.dictionaries.css_declarations.keys())

            if self.dictionaries.css_declarations[declaration_property]:
                value = self.close_brackets(random.choice(self.dictionaries.css_declarations[declaration_property]))

            # css function
            while "$FI_CSS_FUNCTION" in value:
                value = self.generate_css_function()

            if not value and self.morelikely():
                # fuzz value
                value = random.choice(self.fuzz_values)

            declaration = "%s: %s;" % (declaration_property, value)
            declarations.append(declaration)

        return declarations


    def generate_css(self, existing_tags):
        rules = []

        for r in range(random.randint(1, self.MAX_CSS_RULES)):
            rule = []

            selector = self.close_brackets(random.choice(self.dictionaries.css_selector_gadgets))
            rule.append("%s {" % selector)

            declarations = self.generate_css_declarations()
            for declaration in declarations:
                rule.append(declaration)

            rule.append("}")

            rule = "\n".join(rule)

            # tag
            while "$FI_TAG" in rule:
                if existing_tags and self.morelikely():
                    tags = existing_tags
                else:
                    tags = self.dictionaries.html_tags.keys()

                rule = re.sub(r"\$FI_TAG", random.choice(tags), rule, 1)

            # identifiers
            while "$FI_IDENTIFIER" in rule:
                rule = re.sub(r"\$FI_IDENTIFIER", random.choice(self.identifiers), rule, 1)

            rules.append(rule)

        return rules


    def generate_js(self, existing_tags):
        js = "function fuzz() {\n"
        gadgets = []

        for g in range(random.randint(1, self.MAX_JS_GADGETS)):
            gadget = random.choice(self.dictionaries.js_gadgets)

            # identifiers
            while "$FI_IDENTIFIER" in gadget:
                gadget = re.sub(r"\$FI_IDENTIFIER", random.choice(self.identifiers), gadget, 1)

            # functions
            while "$FI_JS_FUNCTION" in gadget:
                gadget = re.sub(r"\$FI_JS_FUNCTION", self.generate_js_method("window"), gadget, 1)

            # literals
            while "$FI_JS_LITERAL" in gadget:
                gadget = re.sub(r"\$FI_JS_LITERAL", random.choice(self.fuzz_values), gadget, 1)

            # object methods
            while "$FI_JS_OBJECT.$FI_JS_METHOD" in gadget:
                js_object = self.generate_js_object(existing_tags)
                gadget = re.sub(r"\$FI_JS_OBJECT\.\$FI_JS_METHOD", self.generate_js_method(js_object), gadget, 1)

            # object properties
            while "$FI_JS_OBJECT.$FI_JS_PROPERTY" in gadget:
                js_object = self.generate_js_object(existing_tags)
                gadget = re.sub(r"\$FI_JS_OBJECT\.\$FI_JS_PROPERTY", self.generate_js_property(js_object), gadget, 1)

            # objects
            while "$FI_JS_OBJECT" in gadget:
                js_object = self.generate_js_object(existing_tags)
                gadget = re.sub(r"\$FI_JS_OBJECT", js_object, gadget, 1)

            # rogue methods
            while "$FI_JS_METHOD" in gadget:
                logging.warn("rogue js method: %s", gadget)

                gadget = re.sub(r"\$FI_JS_METHOD", self.generate_js_method(), gadget, 1)

            # rogue properties
            while "$FI_JS_PROPERTY" in gadget:
                logging.warn("rogue js property: %s", gadget)

                gadget = re.sub(r"\$FI_JS_PROPERTY", self.generate_js_property(), gadget, 1)

            # close brackets
            gadget = self.close_brackets(gadget)

            # end statements with ;
            if gadget[-1] not in [";", "}", "+"]:
                gadget += ";"

            # try/catch gadget
            # @DEBUG disable for a bit
            #gadget = "try { %s } catch(e) {}" % gadget
            gadgets.append(gadget)

        # @DEBUG
        #gadget = "try { %s } catch(e) {}" % "alert('debug');"
        #gadgets.append(gadget)

        js += "\n".join(gadgets)
        js += "\n}"

        return js


    def generate_js_object(self, existing_tags=None):
        if existing_tags and self.morelikely():
            objects = ["document.createElement('%s')" % t.lower() for t in existing_tags]
        else:
            objects = self.dictionaries.js_objects.keys()

        js_object = random.choice(objects)

        return js_object


    def generate_js_property(self, obj=None):
        if obj:
            object_name = obj
        else:
            object_name = random.choice(self.dictionaries.js_objects.keys())

        object_property = self.close_brackets(random.choice(self.dictionaries.js_objects[object_name]["properties"]))
        if not object_property:
            logging.warn("object %s doesn't have any properties", object_name)

            # make one up
            if self.morelikely():
                object_property = random.choice(self.fuzz_values)
            else:
                object_property = random.choice(self.identifiers)

        obj_property = "%s.%s" % (object_name, object_property)

        return obj_property


    def generate_js_method(self, obj=None):
        if obj:
            object_name = obj 
        else:
            object_name = random.choice(self.dictionaries.js_objects.keys())

        method_name = random.choice(self.dictionaries.js_objects[object_name]["methods"].keys())
        if not method_name:
            logging.warn("object %s doesn't have any methods", object_name)

        # real args
        if self.dictionaries.js_objects[object_name]["methods"][method_name]:
            args = random.choice(self.dictionaries.js_objects[object_name]["methods"][method_name])
            args = self.close_brackets(args)

        # random args
        elif self.lesslikely():
            args = []
            for a in range(random.randint(1, self.MAX_JS_METHOD_ARGS)):
                if self.onein(2):
                    arg = random.choice(self.fuzz_values)
                else:
                    arg = random.choice(self.identifiers)

                args.append(arg)

            args = ",".join(args)

        # no args
        else:
            args = ""

        method  = "%s.%s(%s)" % (object_name, method_name, args)

        return method


    def morelikely(self):
        return not self.onein(4)


    def lesslikely(self):
        return self.onein(4)


    @staticmethod
    def onein(x):
        result = random.randint(0, (x-1)) == 1

        return result


    @staticmethod
    def init_fuzz_values():
        values = []

        for label in ["", "deg", "px", "%"]:
            for i in range(33):
                values.append(str(2**i-1) + label)
                values.append(str(2**i) + label)
                values.append(str(2**i+1) + label)

                values.append(str(-(2**i-1)) + label)
                values.append(str(-(2**i)) + label)
                values.append(str(-(2**i+1)) + label)

                values.append(str(float(2**i-1)) + label)
                values.append(str(float(2**i)) + label)
                values.append(str(float(2**i+1)) + label)

                values.append(str(float(-(2**i-1))) + label)
                values.append(str(float(-(2**i))) + label)
                values.append(str(float(-(2**i+1))) + label)

                values.append(str(float("%d.%d" % (2**i-1, 2**i-1))) + label)
                values.append(str(float("%d.%d" % (2**i, 2**i))) + label)
                values.append(str(float("%d.%d" % (2**i+1, 2**i+1))) + label)

                values.append(str(float("%d.%d" % (-(2**i-1), 2**i-1))) + label)
                values.append(str(float("%d.%d" % (-(2**i), 2**i))) + label)
                values.append(str(float("%d.%d" % (-(2**i+1), 2**i+1))) + label)

        for i in range(33):
            values.append("'%s'" % datetime.datetime.fromtimestamp(2**i-1).isoformat())
            values.append("'%s'" % datetime.datetime.fromtimestamp(2**i).isoformat())
            values.append("'%s'" % datetime.datetime.fromtimestamp(2**i+1).isoformat())

        values.append("")
        values.append("''")
        values.append("null")
        values.append("NULL")
        values.append("undefined")
        values.append("true")
        values.append("false")
        values.append("#000000")
        values.append("#FFFFFF")
        values.append(".")
        values.append("..")
        values.append("../")
        values.append("..\\\\")
        values.append(">")
        values.append("<")
        values.append("%x%x%x%x%x%n%n%n%n%n")

        for i in range(8):
            values.append("A"*(2**i))
            values.append("\x00"*(2**i))
            values.append("%00"*(2**i))
            values.append("&#x00;"*(2**i))
            values.append("\r"*(2**i))
            values.append("\n"*(2**i))
            values.append("\r\n"*(2**i))
            values.append("\t"*(2**i))
            values.append(" "*(2**i))

        for i in range(2, 32):
            csv1 = []
            csv2 = []
            for j in range(i):
                csv1.append(str(j))
                csv2.append("AAAA")

            values.append(",".join(csv1))
            values.append(",".join(csv2))

        unique = list(set(values))

        return unique 


    @staticmethod
    def close_brackets(gadget):
        curly = 0
        round_b = 0
        square = 0
        quotes = 0

        for c in gadget:
            if c == "{":
                curly += 1

            if c == "}":
                curly -= 1

            if c == "(":
                round_b += 1

            if c == ")":
                round_b -= 1

            if c == "[":
                square += 1

            if c == "]":
                square -= 1

            if c == "'":
                quotes += 1

        while curly > 0:
            gadget += "}"
            curly -= 1

        while curly < 0:
            gadget = "{" + gadget
            curly += 1

        while round_b > 0:
            gadget += ")"
            round_b -= 1

        while round_b < 0:
            gadget = "(" + gadget
            round_b += 1

        while square > 0:
            gadget += "]"
            square -= 1

        while square < 0:
            gadget = "[" + gadget
            square += 1

        while quotes % 2:
            gadget += "'"
            quotes += 1

        return gadget
