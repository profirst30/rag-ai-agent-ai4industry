# Guide d'installation d'OTOROSHI

### Télécharger 

#### Otoroshi
``` bash
https://github.com/MAIF/otoroshi/releases
```
#### LLM Extension :
``` bash
https://github.com/cloud-apim/otoroshi-llm-extension/releases
```

### Lancer 
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



