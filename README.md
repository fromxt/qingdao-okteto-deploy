# How to build image and deploy the python App on Okteto 

## Step 0: Install the Okteto and Kubectl CLI 
 - Kubectl CLI https://okteto.com/docs/enterprise/gke/index.html#Installing-kubectl
 - Okteto Cli https://okteto.com/docs/getting-started/installation
 
## Step 1: Build and Push images into the Okteto Registry
- Get a local version of the App by executing the following commands:
```
git clone https://github.com/<github id>/qingdao-okteto-deploy.git 
cd qingdao-okteto-deploy
okteto login
okteto namespace
```

If you are using the okteto CLI, all you need to do is run `okteto login` once. This will download the required tokens and      certificates     required to push and pull images to the Okteto Registry.

- Write `Dockerfile` and build your images by executing the following commands:
```
okteto build -t registry.cloud.okteto.net/<github id>/qingdao:python .
```
The okteto CLI is automatically configured to interact with the Okteto Registry. Just make sure that you are using the registry URL with your Okteto namespace.

## Step 2: Write `k8s.yml` and deploy the App on Okteto
The `k8s.yml` file contains the Kubernetes manifests of the App. Deploy a dev version of the application by executing:
```
 kubectl apply -f k8s.yml
```
## Step 3: Login 
You can access the App https://qingdao-github_id.cloud.okteto.net/qingdao

# Reference
- https://github.com/teenyda/qingdao
