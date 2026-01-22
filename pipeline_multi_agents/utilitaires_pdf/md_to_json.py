import json
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_all_caps(text):
    letters = re.sub(r'[^a-zA-ZÀ-ÿ]', '', text)
    return letters.isupper() if letters else False

def starts_with_number(text):
    return re.match(r'^\d+', text.strip()) is not None

def process_md_contextual():
    script_dir = Path(__file__).resolve().parent
    export_dir = script_dir / "exports_markdown"
    
    if not export_dir.exists():
        export_dir = script_dir.parent / "markdown"
    
    output_json = script_dir.parent / "json" / "knowledge_base.json"

    md_files = list(export_dir.glob("*.md"))
    if not md_files:
        logger.error(f"Aucun fichier Markdown trouvé dans {export_dir}")
        return
    
    md_file_path = md_files[0]
    logger.info(f"Analyse contextuelle de : {md_file_path.name}")

    with open(md_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    processed_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            processed_lines.append({
                "raw": line,
                "clean": stripped,
                "is_header": stripped.startswith('##'),
                "content": re.sub(r'^#+\s+', '', stripped)
            })

    chunks = []
    current_headings = {1: "Préface", 2: ""}
    current_text = []
    chunk_id = 0

    def save_chunk(text_list, headings_dict, cid):
        full_text = "".join(text_list).strip()
        if full_text:
            active_headings = [headings_dict[i] for i in [1, 2] if headings_dict[i]]
            chunks.append({
                "chunk_id": cid,
                "headings": active_headings,
                "text": full_text
            })
            return cid + 1
        return cid

    for i in range(len(processed_lines)):
        item = processed_lines[i]
        content = item['content']
        new_level = None

        if item['is_header']:
            if starts_with_number(content):
                new_level = 2
            
            elif is_all_caps(content):
                is_false_positive = False
                
                if i > 0:
                    prev = processed_lines[i-1]
                    if not prev['is_header'] and is_all_caps(prev['clean']):
                        is_false_positive = True
                
                if not is_false_positive and i < len(processed_lines) - 1:
                    nxt = processed_lines[i+1]
                    if not nxt['is_header'] and is_all_caps(nxt['clean']):
                        is_false_positive = True
                
                if not is_false_positive:
                    new_level = 1
                else:
                    logger.info(f"Ignoré (Élément de schéma) : {content}")

        if new_level:
            chunk_id = save_chunk(current_text, current_headings, chunk_id)
            current_text = []
            current_headings[new_level] = content
            if new_level == 1:
                current_headings[2] = ""
            logger.info(f"[{new_level}] {content}")
        else:
            current_text.append(item['raw'])

    save_chunk(current_text, current_headings, chunk_id)

    output_json.parent.mkdir(exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    logger.info(f"JSON généré avec {len(chunks)} chunks.")

if __name__ == "__main__":
    process_md_contextual()