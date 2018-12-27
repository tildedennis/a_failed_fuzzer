# notes

my side project for 2016 was to try and write an internet explorer fuzzer. while i learned quite a bit in the process, it ultimately didn't find any bugs. i haven't looked at it in a long time, so it'll require some stick poking to get going.

`scrapers/` contains scrapers to pull down code examples from various sources into `corpus/`:

```
dennis@ipa:~/dump/a_failed_fuzzer$ mkdir -p corpus/w3schools
dennis@ipa:~/dump/a_failed_fuzzer$ cd scrapers/w3schools/
dennis@ipa:~/dump/a_failed_fuzzer/scrapers/w3schools$ python examples.py http://www.w3schools.com/html/default.asp html 
tryhtml_color_names
tryhtml_color_hex
tryhtml_color_rgba
tryhtml_color_border
tryhtml_color_rgb
...
dennis@ipa:~/dump/a_failed_fuzzer/scrapers/w3schools$ ls ../../corpus/w3schools/
tryhtml_color_border   tryhtml_color_hex      tryhtml_color_names    tryhtml_color_rgb      tryhtml_color_rgba
...
```

running `fuzz_ie.py` with the `-p` argument parses the corpus into various pieces and caches them into the `pieces/` directory:

```
dennis@ipa:~/dump/fuzz_ie$ python fuzz_ie.py -p                                                                                                                                         
[INFO] 2018-12-27 01:36:22: --------------------------------
[INFO] 2018-12-27 01:36:22: log opened
[INFO] 2018-12-27 01:36:22: read 93 html events
[INFO] 2018-12-27 01:36:22: read 63 js reserved words
[INFO] 2018-12-27 01:36:22: read 11 js operators
[INFO] 2018-12-27 01:36:22: read 351 js objects
[INFO] 2018-12-27 01:37:15: parsed 14498 files from corpus
[INFO] 2018-12-27 01:37:15: parsed 272 html tags
[INFO] 2018-12-27 01:37:15: parsed 417 html attributes
[INFO] 2018-12-27 01:37:15: parsed 408 css selector gadgets
[INFO] 2018-12-27 01:37:15: parsed 483 css declarations
[INFO] 2018-12-27 01:37:15: parsed 95 css functions
[INFO] 2018-12-27 01:37:15: parsed 5718 js gadgets
[INFO] 2018-12-27 01:37:15: pieces dumped
[INFO] 2018-12-27 01:37:15: 2532 fuzz values
[INFO] 2018-12-27 01:37:15: 3 identifiers
<style>
foreignobject:-moz-read-write {
-webkit-transition-property: width;
-webkit-text-decoration-color: red;
}
</style>
<script>
function fuzz() {
(window.clearInterval(oInterval)')';
x = [-4097.4097deg, -5.0, 2047%, 16383.0px];
}
</script>
<script>setInterval(fuzz, 2000);</script>
<body onload="fuzz();">
<foreignobject>
<meter onkeyup="fuzz();">
</body>
dennis@ipa:~/dump/fuzz_ie$ ls pieces/                                                                                                                                                   
css_declarations       css_selector_gadgets   html_events            js_gadgets             js_operators
css_functions          html_attributes        html_tags              js_objects             js_reserved_words
```

running `fuzz_ie.py` without any arguments will generate test cases:

```
dennis@ipa:~/dump/fuzz_ie$ python fuzz_ie.py                                                                                                                                            
[INFO] 2018-12-27 01:40:45: --------------------------------
[INFO] 2018-12-27 01:40:45: log opened
[INFO] 2018-12-27 01:40:45: read 93 html events
[INFO] 2018-12-27 01:40:45: read 63 js reserved words
[INFO] 2018-12-27 01:40:45: read 11 js operators
[INFO] 2018-12-27 01:40:45: read 351 js objects
[INFO] 2018-12-27 01:40:45: using cached pieces
[INFO] 2018-12-27 01:40:45: parsed 272 html tags
[INFO] 2018-12-27 01:40:45: parsed 417 html attributes
[INFO] 2018-12-27 01:40:45: parsed 408 css selector gadgets
[INFO] 2018-12-27 01:40:45: parsed 483 css declarations
[INFO] 2018-12-27 01:40:45: parsed 95 css functions
[INFO] 2018-12-27 01:40:45: parsed 5718 js gadgets
[INFO] 2018-12-27 01:40:45: 2532 fuzz values
[INFO] 2018-12-27 01:40:45: 3 identifiers
<style>
mroot:-moz-read-only {
-webkit-animation: mymove 2s infinite linear alternate;
}
</style>
<script>
function fuzz() {
function window.blur() {},false,false;
* OPENED 0;
}
</script>
<script>setInterval(fuzz, 6000);</script>
<body onload="fuzz();">
<pattern height="30" y="0">
<animate ontouchstart="fuzz();">
</body>

dennis@ipa:~/dump/fuzz_ie$ python fuzz_ie.py  
[INFO] 2018-12-27 01:40:47: --------------------------------
[INFO] 2018-12-27 01:40:47: log opened
[INFO] 2018-12-27 01:40:47: read 93 html events
[INFO] 2018-12-27 01:40:47: read 63 js reserved words
[INFO] 2018-12-27 01:40:47: read 11 js operators
[INFO] 2018-12-27 01:40:47: read 351 js objects
[INFO] 2018-12-27 01:40:47: using cached pieces
[INFO] 2018-12-27 01:40:47: parsed 272 html tags
[INFO] 2018-12-27 01:40:47: parsed 417 html attributes
[INFO] 2018-12-27 01:40:47: parsed 408 css selector gadgets
[INFO] 2018-12-27 01:40:47: parsed 483 css declarations
[INFO] 2018-12-27 01:40:47: parsed 95 css functions
[INFO] 2018-12-27 01:40:47: parsed 5718 js gadgets
[INFO] 2018-12-27 01:40:47: 2532 fuzz values
[INFO] 2018-12-27 01:40:47: 3 identifiers
<style>
menuitem.this:hover meta[type='radio']:checked ~ select {
position: sticky;
}
</style>
<script>
function fuzz() {
y = eval(x);  ;
}
</script>
<script>setInterval(fuzz, 4000);</script>
<body onload="fuzz();">
<menuitem xmlns:t="urn:schemas-microsoft-com:time" label="New...">
<pattern patternunits="userSpaceOnUse">
<meta scheme="customer" charset="utf-8">
</body>
```

"fuzzing" mode can be turned on by passing the `-f` argument. i was using https://github.com/SkyLined/cBugId for execution, debugging, crash detection, and initial triage, but i believe that project has changed quite a bit since. the `fuzz` and `save_crash` functions in `fuzz_ie.py` will likely need updating to get it working again.
