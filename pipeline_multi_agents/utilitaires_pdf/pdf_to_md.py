import logging
from pathlib import Path
from docling.document_converter import DocumentConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_all_pdfs_to_md():
    base_dir = Path(__file__).resolve().parent.parent
    
    pdf_dir = base_dir / "pdf"
    if not pdf_dir.exists():
        logger.error(f"Dossier PDF introuvable : {pdf_dir}")
        return
    
    logger.info(f"Recherche en cours dans : {pdf_dir}")

    output_dir = base_dir / "markdown"
    output_dir.mkdir(exist_ok=True)

    pdf_files = [f for f in pdf_dir.iterdir() if f.suffix.lower() == '.pdf']

    if not pdf_files:
        logger.warning(f"Aucun fichier PDF trouvé dans {pdf_dir}")
        return

    logger.info(f"{len(pdf_files)} PDF(s) détecté(s).")
    
    converter = DocumentConverter()

    for pdf_path in pdf_files:
        try:
            logger.info(f"Conversion : {pdf_path.name}...")
            result = converter.convert(str(pdf_path))
            md_content = result.document.export_to_markdown()
            
            output_file = output_dir / f"{pdf_path.stem}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            logger.info(f"Terminé : {output_file.name}")
        except Exception as e:
            logger.error(f"Erreur sur {pdf_path.name} : {e}")

if __name__ == "__main__":
    convert_all_pdfs_to_md()