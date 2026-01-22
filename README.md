# Projet GROUPE 3 

Cette version utilise otoroshi avec le systeme de tool et des json générer sans Embedding. 
Les json sont mis directement dans la definition du tool (méthode directe utilisée par manque de temps dans le cas ou une piste plus élaboré ne fonctionner pas cf. branch nobel_version).

### Télécharger 

#### Otoroshi
``` bash
https://github.com/MAIF/otoroshi/releases
```
#### LLM Extension :
``` bash
https://github.com/cloud-apim/otoroshi-llm-extension/releases
```
Ajouter la .jar a la racine du projet puis lancer. 
### Lancer 

Renommer les .jar sans les versions 
nom des jar : 
- otoroshi.jar
- 
#### Pour windows 
```bash
java -cp "otoroshi-llm-extension.jar;otoroshi.jar" -Dotoroshi.adminLogin=admin -Dotoroshi.adminPassword=password -Dotoroshi.storage=file play.core.server.ProdServerStart
```

#### Pour Linux : 
```bash
java -cp "otoroshi-llm-extension.jar:otoroshi.jar" -Dotoroshi.adminLogin=admin -Dotoroshi.adminPassword=password -Dotoroshi.storage=file play.core.server.ProdServerStart
```

### Lancer l'interface pour tester 
```bash
python -m http.server 9000
```

### Lien
#### Interface de chat bot 
http://ai4industry.oto.tools:8080/chat

### Interface admin 
http://otoroshi.oto.tools:8080

### Instruction 

Pour les models j'utilise GROQ qui donne des tokens gratuit sur plusieurs models.
Pour faire ça : 
1. Aller dans LLM provider depuis l'interface admin
2. cliquer sur OpenAI provider (le seul normalement)
3. Inscrivez-vous sur groq puis créer une clé API https://console.groq.com/keys
4. Changer la clé dans API Token 
5. Selectionner un model (j'ai testé openai/gtp-oss-120b et 20b qui marche assez bien) mais faites attentions tous les models ne peuvent pas utiliser les tools donc si ça marche pas essayer un autre.


#### Utilsation 
Le chat est fait pour répondre à des questions uniquement en rapport avec les DDRM qu'il possède. (departement 73,79,86)


