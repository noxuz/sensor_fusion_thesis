# -*- coding: utf-8 -*-
import zipfile
from collections import Counter
from lxml import etree
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
p = Path(r"C:\Users\noxuz\OneDrive\Documentos\000000LETESIS\sensor_fusion_thesis\tesis_docx\TOG_SENSOR_FUSION.docx")
with zipfile.ZipFile(p) as z:
    doc = etree.fromstring(z.read("word/document.xml"))
szs = Counter()
for om in doc.findall(f".//{M}oMath"):
    for r in om.findall(f".//{M}r"):
        sz = r.find(f"{W}rPr/{W}sz")
        szs[sz.get(f"{W}val") if sz is not None else "none"] += 1
print(dict(szs))
