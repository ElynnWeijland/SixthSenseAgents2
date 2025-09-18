# Maak de infra-new directory aan
mkdir -p aifoundry-basics

# Ga naar de nieuwe directory
cd aifoundry-basics/

# Download alle bestanden van de AI Foundry basics quickstart template
echo "Downloading AI Foundry quickstart template files..."

# Download de main template files
curl -o main.bicep "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/main.bicep"

curl -o azuredeploy.json "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/azuredeploy.json"

curl -o azuredeploy.parameters.json "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/azuredeploy.parameters.json"

curl -o README.md "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/README.md"

curl -o metadata.json "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/metadata.json"

# Download modules directory
mkdir -p modules

# Download de module bestanden
curl -o modules/storage.bicep "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/modules/storage.bicep"

curl -o modules/keyvault.bicep "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/modules/keyvault.bicep"

curl -o modules/applicationinsights.bicep "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/modules/applicationinsights.bicep"

curl -o modules/cognitiveservices.bicep "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/modules/cognitiveservices.bicep"

curl -o modules/aiproject.bicep "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/modules/aiproject.bicep"

curl -o modules/aihub.bicep "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/quickstarts/microsoft.machinelearningservices/aifoundry-basics/modules/aihub.bicep"

# Controleer of alle bestanden zijn gedownload
echo "Downloaded files:"
find . -type f -name "*.bicep" -o -name "*.json" -o -name "*.md" | sort
