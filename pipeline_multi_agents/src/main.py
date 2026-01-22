import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
import re
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OLLAMA_CONFIG = {
    'base_url': 'http://localhost:11434/v1',
    'api_key': 'ollama',
    'model': 'qwen3:1.7b',
    'timeout': 60
}

RISK_SYNONYMS = {
    'inondation': ['inondation', 'crue', 'débordement', 'submersion'],
    'seisme': ['séisme', 'seisme', 'tremblement de terre', 'sismique'],
    'nucleaire': ['nucléaire', 'nucleaire', 'centrale nucléaire', 'radioactif'],
    'tmd': ['tmd', 'transport de matières dangereuses', 'transport matières dangereuses'],
    'industriel': ['industriel', 'usine', 'seveso', 'installation classée'],
    'mouvement_terrain': ['mouvement de terrain', 'glissement', 'éboulement', 'effondrement'],
    'radon': ['radon', 'gaz radon'],
    'feu_foret': ['feu de forêt', 'incendie forestier', 'feux de forêts']
}

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[àâä]', 'a', text)
    text = re.sub(r'[éèêë]', 'e', text)
    text = re.sub(r'[îï]', 'i', text)
    text = re.sub(r'[ôö]', 'o', text)
    text = re.sub(r'[ùûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    return text

def match_risk_type(query: str) -> Optional[str]:
    query_norm = normalize_text(query)
    
    for risk_key, synonyms in RISK_SYNONYMS.items():
        for synonym in synonyms:
            if normalize_text(synonym) in query_norm:
                return risk_key
    return None

class KnowledgeBaseTool:
    def __init__(self, json_path: str = "knowledge_base.json"):
        self.json_path = Path(json_path)
        if not self.json_path.is_absolute():
            self.json_path = Path(__file__).parent / self.json_path
        
        try:
            self.data = self._load_data()
            logger.info(f"Base de connaissances chargée : {len(self.data)} chunks")
        except FileNotFoundError:
            logger.error(f"Fichier introuvable : {self.json_path}")
            self.data = []
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON : {e}")
            self.data = []
    
    def _load_data(self) -> List:
        with self.json_path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _is_relevant_chunk(self, chunk: Dict, target_risk: str, exclude_risks: List[str]) -> bool:
        headings = [normalize_text(h) for h in chunk.get('headings', [])]
        
        risk_in_headings = any(target_risk in h for h in headings)
        
        if not risk_in_headings:
            return False
        
        for exclude_risk in exclude_risks:
            if any(exclude_risk in h for h in headings):
                return False
        
        return True

    def get_smart_content(self, risk_name: str, commune: str = "inconnu") -> Optional[Dict]:
        logger.info(f"[TOOL] Recherche : risque='{risk_name}' | commune='{commune}'")
        
        target_risk = normalize_text(risk_name)
        commune_norm = normalize_text(commune) if commune != "inconnu" else None
        
        all_risks = list(RISK_SYNONYMS.keys())
        exclude_risks = [normalize_text(r) for r in all_risks if normalize_text(r) != target_risk]
        
        general_info = []
        local_info = []
        commune_found = False
        
        for idx, chunk in enumerate(self.data):
            if not self._is_relevant_chunk(chunk, target_risk, exclude_risks):
                continue
            
            headings = chunk.get('headings', [])
            text_content = chunk.get('text', '').strip()
            text_lower = normalize_text(text_content)
            
            if len(text_content) < 50:
                continue
            
            is_table_listing = any(
                keyword in ' '.join([normalize_text(h) for h in headings]) 
                for keyword in ['liste des communes', 'tableau', 'inventaire']
            )
            
            if not is_table_listing and len(text_content) < 3000:
                general_info.append({
                    'text': text_content,
                    'path': ' > '.join(headings),
                    'length': len(text_content)
                })
            
            if commune_norm and commune_norm in text_lower:
                commune_found = True
                extract = self._extract_commune_context(text_content, commune, max_chars=800)
                local_info.append({
                    'text': extract,
                    'path': ' > '.join(headings)
                })
                logger.info(f"Commune '{commune}' trouvée dans chunk #{idx}")

        if not general_info and not local_info:
            logger.warning(f"Aucun contenu trouvé pour '{risk_name}'")
            return None

        general_info.sort(key=lambda x: x['length'])
        
        result = {
            "nom_risque": risk_name.upper(),
            "commune_cible": commune,
            "est_specifique_local": commune_found,
            "contexte_general": self._format_context(general_info[:3]),
            "contexte_local": self._format_context(local_info[:2])
        }
        
        logger.info(f"Resultat : {len(general_info)} général(s), {len(local_info)} local(aux)")
        return result

    def _extract_commune_context(self, text: str, commune: str, max_chars: int = 800) -> str:
        commune_norm = normalize_text(commune)
        text_lower = normalize_text(text)
        
        pos = text_lower.find(commune_norm)
        if pos == -1:
            return text[:max_chars]
        
        start = max(0, pos - max_chars // 2)
        end = min(len(text), pos + max_chars // 2)
        
        extract = text[start:end]
        if start > 0:
            extract = "..." + extract
        if end < len(text):
            extract = extract + "..."
        
        return extract

    def _format_context(self, info_list: List[Dict]) -> str:
        if not info_list:
            return ""
        
        formatted = []
        for item in info_list:
            formatted.append(f"[Source: {item['path']}]\n{item['text']}")
        
        return "\n\n".join(formatted)

class CoordinatorAgent:
    SYSTEM_PROMPT = """Tu es un extracteur de données pour un système de gestion des risques.

MISSION : Analyser la requête utilisateur et extraire 2 informations clés.

RÈGLES STRICTES :
1. Retourne UNIQUEMENT un JSON valide (aucun texte avant/après)
2. Format exact : {"commune": "...", "risque": "..."}
3. Si la ville n'est pas explicitement citée → "commune": "inconnu"
4. Si le type de risque n'est pas identifiable → "risque": "inconnu"
5. Normalise les noms (ex: "St-Pierre" → "Saint-Pierre")

TYPES DE RISQUES VALIDES :
- inondation, seisme, nucleaire, tmd, industriel, mouvement_terrain, radon, feu_foret

EXEMPLES :
User: "Les risques nucléaires à Civaux"
→ {"commune": "Civaux", "risque": "nucleaire"}

User: "Parle moi des séismes"
→ {"commune": "inconnu", "risque": "seisme"}

User: "Que faire en cas d'inondation à Bordeaux ?"
→ {"commune": "Bordeaux", "risque": "inondation"}"""
    
    def __init__(self, client: OpenAI):
        self.client = client
    
    def analyze(self, query: str) -> Dict:
        try:
            logger.info(f"[COORD] Analyse de : '{query}'")
            
            response = self.client.chat.completions.create(
                model=OLLAMA_CONFIG['model'],
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0,
                response_format={"type": "json_object"},
                timeout=OLLAMA_CONFIG['timeout']
            )
            
            result = json.loads(response.choices[0].message.content)
            
            result['commune'] = result.get('commune', 'inconnu').strip()
            result['risque'] = normalize_text(result.get('risque', 'inconnu'))
            
            logger.info(f"[COORD] Extraction : {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[COORD] Erreur JSON : {e}")
            return {"commune": "inconnu", "risque": "inconnu"}
        except Exception as e:
            logger.error(f"[COORD] Erreur API : {e}")
            return {"commune": "inconnu", "risque": "inconnu"}

class WriterAgent:
    SYSTEM_PROMPT = """Tu es un expert en communication des risques pour les DICRIM (Documents d'Information Communal sur les Risques Majeurs).

MISSION : Rédiger une fiche informative claire et rassurante.

RÈGLES D'OR :
1. FOCUS ABSOLU : Ne parle QUE du risque demandé (ex: si c'est "nucléaire", ignore le radon même s'il est dans les sources)
2. STRUCTURE OBLIGATOIRE :
   ## 🔍 Nature du risque
   ## 📍 Situation locale
   ## ⚠️ Consignes de sécurité

3. STYLE :
   - Ton pédagogique et rassurant
   - Phrases courtes et claires
   - Pas de jargon technique excessif
   - Utilise des listes à puces pour les consignes

4. GESTION DES DONNÉES MANQUANTES :
   - Si 'contexte_general' est vide → "Les informations générales ne sont pas disponibles actuellement."
   - Si 'est_specifique_local' est False → "Cette commune n'est pas spécifiquement mentionnée dans les documents disponibles."

5. LONGUEUR : Entre 200 et 600 mots maximum.

EXEMPLE DE TON :
"Le risque nucléaire concerne les installations utilisant des matières radioactives. En France, les centrales sont soumises à des contrôles stricts. En cas d'alerte, restez chez vous et suivez les consignes des autorités."

INTERDIT :
❌ Mélanger plusieurs risques
❌ Inventer des informations
❌ Utiliser un ton alarmiste"""

    def __init__(self, client: OpenAI):
        self.client = client
    
    def write(self, context: Dict) -> str:
        try:
            logger.info(f"[WRITER] Rédaction pour : {context['nom_risque']}")
            
            prompt = self._build_prompt(context)
            
            response = self.client.chat.completions.create(
                model=OLLAMA_CONFIG['model'],
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                timeout=OLLAMA_CONFIG['timeout']
            )
            
            result = response.choices[0].message.content
            logger.info(f"[WRITER] Fiche générée ({len(result)} caractères)")
            return result
            
        except Exception as e:
            logger.error(f"[WRITER] Erreur génération : {e}")
            return f"Erreur lors de la génération de la fiche pour {context['nom_risque']}. Veuillez réessayer."

    def _build_prompt(self, context: Dict) -> str:
        prompt_parts = [
            f"RISQUE À TRAITER : {context['nom_risque']}",
            f"COMMUNE : {context['commune_cible']}",
            f"PRÉSENCE LOCALE : {'OUI' if context['est_specifique_local'] else 'NON'}",
            "",
            "=== CONTEXTE GÉNÉRAL ==="
        ]
        
        if context['contexte_general']:
            prompt_parts.append(context['contexte_general'][:4000])
        else:
            prompt_parts.append("(Aucune information générale disponible)")
        
        prompt_parts.append("\n=== CONTEXTE LOCAL ===")
        
        if context['contexte_local']:
            prompt_parts.append(context['contexte_local'][:2000])
        else:
            prompt_parts.append("(Aucune mention spécifique de cette commune)")
        
        prompt_parts.append("\n---\nRédige maintenant la fiche DICRIM en respectant la structure imposée.")
        
        return "\n".join(prompt_parts)

class TruthValidatorAgent:
    SYSTEM_PROMPT = """Tu es un vérificateur de données spécialisé dans la validation des informations sur les risques.

MISSION : Comparer la fiche DICRIM générée avec les données source (ground truth) et détecter les incohérences.

RÈGLES STRICTES :
1. Analyser chaque affirmation de la fiche générée
2. Vérifier si elle correspond aux données source
3. Identifier les éventuelles hallucinations ou extrapolations
4. Noter la conformité globale

CRITÈRES DE VÉRIFICATION :
✅ CONFORME : L'information est présente dans les sources
⚠️ PARTIELLEMENT CONFORME : L'information est déduite mais plausible
❌ NON CONFORME : L'information contredit ou invente des données

RETOUR : Un JSON structuré avec :
- score_conformite (0-100)
- incoherences_detectees (liste)
- informations_manquantes (liste)
- recommandations (liste)"""

    def __init__(self, client: OpenAI):
        self.client = client
    
    def validate(self, generated_fiche: str, source_context: Dict) -> Dict:
        try:
            logger.info(f"[VALIDATOR] Vérification de la fiche générée")
            
            validation_prompt = self._build_validation_prompt(generated_fiche, source_context)
            
            response = self.client.chat.completions.create(
                model=OLLAMA_CONFIG['model'],
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"},
                timeout=OLLAMA_CONFIG['timeout']
            )
            
            validation_result = json.loads(response.choices[0].message.content)
            
            logger.info(f"[VALIDATOR] Score de conformité : {validation_result.get('score_conformite', 'N/A')}%")
            
            incohérences = validation_result.get('incoherences_detectees', [])
            if incohérences:
                logger.warning(f"[VALIDATOR] Incohérences détectées : {len(incohérences)}")
                for inc in incohérences[:3]:
                    logger.warning(f"   - {inc}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"[VALIDATOR] Erreur de validation : {e}")
            return {
                "score_conformite": 0,
                "incoherences_detectees": ["Erreur lors de la validation"],
                "informations_manquantes": [],
                "recommandations": ["Revérifier manuellement la fiche"]
            }
    
    def _build_validation_prompt(self, fiche: str, context: Dict) -> str:
        prompt_parts = [
            "=== FICHE GÉNÉRÉE À VALIDER ===",
            fiche[:3000],
            "\n" + "="*50 + "\n",
            "=== DONNÉES SOURCE (GROUND TRUTH) ===",
            f"Risque : {context.get('nom_risque', 'N/A')}",
            f"Commune : {context.get('commune_cible', 'N/A')}",
            f"Sources spécifiques locales : {'OUI' if context.get('est_specifique_local') else 'NON'}",
            "\n--- CONTEXTE GÉNÉRAL ---",
            context.get('contexte_general', 'Aucune')[:2000],
            "\n--- CONTEXTE LOCAL ---",
            context.get('contexte_local', 'Aucune')[:1000],
            "\n" + "="*50 + "\n",
            "INSTRUCTIONS : Comparez chaque affirmation de la fiche avec les données source.",
            "Retournez un JSON structuré avec le score de conformité et les incohérences détectées."
        ]
        
        return "\n".join(prompt_parts)

class DICRIMOrchestrator:
    def __init__(self):
        try:
            self.client = OpenAI(
                base_url=OLLAMA_CONFIG['base_url'], 
                api_key=OLLAMA_CONFIG['api_key'],
                timeout=OLLAMA_CONFIG['timeout']
            )
            self.kb = KnowledgeBaseTool()
            self.coordinator = CoordinatorAgent(self.client)
            self.writer = WriterAgent(self.client)
            self.validator = TruthValidatorAgent(self.client)
            logger.info("Orchestrateur initialisé avec vérificateur de vérité terrain")
        except Exception as e:
            logger.error(f"Erreur initialisation : {e}")
            raise

    def process(self, query: str) -> str:
        logger.info(f"\n{'='*60}\nNOUVELLE REQUÊTE : {query}\n{'='*60}")
        
        try:
            params = self.coordinator.analyze(query)
            
            if params['risque'] == "inconnu":
                logger.warning("Risque non identifié")
                return self._format_error_response(
                    "Je n'ai pas pu identifier le type de risque dans votre demande.",
                    "Exemples valides : inondation, séisme, nucléaire, transport de matières dangereuses..."
                )
            
            source_data = self.kb.get_smart_content(params['risque'], params['commune'])
            
            if not source_data:
                logger.warning(f"Aucune donnée pour {params['risque']}")
                return self._format_error_response(
                    f"Aucune information disponible pour le risque : {params['risque']}",
                    "Vérifiez que ce risque est bien documenté dans la base de connaissances."
                )
            
            final_response = self.writer.write(source_data)
            
            logger.info("Lancement de la vérification de vérité terrain...")
            validation_result = self.validator.validate(final_response, source_data)
            
            if validation_result.get('score_conformite', 0) < 70:
                logger.warning(f"Fiche potentiellement non-conforme : {validation_result['score_conformite']}%")
            
            self._log_validation_result(validation_result)
            
            logger.info("Traitement terminé avec succès")
            return final_response
            
        except Exception as e:
            logger.error(f"Erreur critique : {e}", exc_info=True)
            return self._format_error_response(
                "Une erreur s'est produite lors du traitement de votre demande.",
                f"Détail technique : {str(e)}"
            )
    
    def _log_validation_result(self, validation_result: Dict):
        logger.info("\n" + "="*60)
        logger.info("RÉSULTAT DE VÉRIFICATION DE VÉRITÉ TERRAIN")
        logger.info("="*60)
        logger.info(f"Score de conformité : {validation_result.get('score_conformite', 'N/A')}%")
        
        incohérences = validation_result.get('incoherences_detectees', [])
        if incohérences:
            logger.info(f"\nIncohérences détectées ({len(incohérences)}) :")
            for i, inc in enumerate(incohérences[:5], 1):
                logger.info(f"  {i}. {inc}")
            if len(incohérences) > 5:
                logger.info(f"  ... et {len(incohérences) - 5} autres")
        else:
            logger.info("Aucune incohérence majeure détectée")
        
        recommandations = validation_result.get('recommandations', [])
        if recommandations:
            logger.info(f"\nRecommandations :")
            for rec in recommandations:
                logger.info(f"  • {rec}")
        
        logger.info("="*60)

    def _format_error_response(self, main_message: str, detail: str = "") -> str:
        response = f"{main_message}"
        if detail:
            response += f"\n\n{detail}"
        return response

def run_tests():
    orchestrator = DICRIMOrchestrator()
    
    test_cases = [
        ("Explique moi le risque nucléaire", "Test général - Nucléaire"),
        ("Quels sont les risques nucléaires à Civaux ?", "Test spécifique - Civaux"),
        ("Y a-t-il des risques d'inondation à Bordeaux ?", "Test ville - Bordeaux"),
        ("Parle moi du radon", "Test radon général"),
        ("Que faire en cas de séisme ?", "Test séisme général"),
        ("Les risques dans ma ville", "Test incomplet - pas de risque"),
    ]
    
    for query, description in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST : {description}")
        print(f"Query: {query}")
        print(f"{'='*70}")
        
        result = orchestrator.process(query)
        print(result)
        print("\n")

if __name__ == "__main__":
    run_tests()