ARG VARIANT="3.8-bullseye"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

RUN pip install flake8
RUN pip install pandas
RUN pip install pipreqs
RUN pip install pydantic
RUN pip install requests
RUN pip install sqlalchemy