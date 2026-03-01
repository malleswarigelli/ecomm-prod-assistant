import importlib.metadata
packages = [
    "langchain",
    "langchain_core",   
    "python-dotenv" 
]

for package in packages:
    try:
        version = importlib.metadata.version(package)
        print(f"{package}=={version}")
    except importlib.metadata.PackageNotFoundError:
        print(f"{package} is not installed.")