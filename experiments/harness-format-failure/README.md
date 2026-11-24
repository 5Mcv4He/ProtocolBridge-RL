# Recorded Harness format failure

The model returned multiple JSON objects and prose-prefixed objects. The original
strict decoder rejected these as parse errors; feedback failed to distinguish a
response-format error from a file-read error. No spec/RTL read succeeded. The model
submitted the untouched stub. The controller stopped that compile to repair the
Harness, retaining reward=null and compile exit 143. This is not a measured RTL
failure. Full external responses remain private. The replacement parser executes
only the first valid allowlisted capability object and explicitly says remaining
objects were not executed. A new trial uses a new frozen manifest.
