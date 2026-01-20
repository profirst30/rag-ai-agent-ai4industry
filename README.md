# Guide d'installation d'OTOROSHI

### Télécharger 

#### Otoroshi
``` bash
curl -L -o otoroshi.jar 'https://github.com/MAIF/otoroshi/releases/download/v17.0.0/otoroshi.jar'
```
#### LLM Extension :
``` bash
curl -L -o otoroshi-llm-extension.jar 'https://github.com/cloud-apim/otoroshi-llm-extension/releases/download/0.0.43/otoroshi-llm-extension_2.12-0.0.43.jar'
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