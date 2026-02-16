from docx import Document
import os

doc_path = r"c:\Users\jzabala\OneDrive - IKERLAN S.COOP\Escritorio\TFG\problemas\TRABAJO DE FIN DE GRADO (1).docx"

doc = Document(doc_path)

output = []
output.append("="*80)
output.append("CONTENIDO DEL TFG")
output.append("="*80)

for para in doc.paragraphs:
    text = para.text.strip()
    if text:
        if para.style.name.startswith('Heading'):
            output.append(f"\n### {text}")
        else:
            output.append(text)

with open("contenido_tfg.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Archivo guardado: contenido_tfg.txt")
print(f"Total de párrafos: {len(output)}")
