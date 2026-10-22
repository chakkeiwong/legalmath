# Direct-copy repair rejected for wrong text hash

The production TextUnit hashes raw UTF-8 bytes. The assessor and new synthetic fixture instead hashed the JSON string. This is a local implementation and fixture defect, not source loss or a package defect. The retained positive baseline failed;27 passing controls do not justify promotion. Use the actual TextUnit constructor for the changed repair and preserve both failed attempts and all costs.
