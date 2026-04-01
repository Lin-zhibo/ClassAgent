### agent.py

为main提供LLM交互

### shell.py

为用户提供交互shell

### main.py

上层封装，合并所有组件

### RAG.py

提供RAG相关功能

RAG 使用langchain+chroma

### memoryManager.py

### prompt.py

所有的提示词均储存在这个文件中

## docs

文档目录

## data

存储可阅读的数据，如知识库

### questions.CSV

问答知识题库

## db

数据库（如sqlite）存储路径，可用于存储知识向量化后的知识库文件

## script

脚本存储目录，存储一些与项目运行无直接关联的脚本（如数据清洗）

## config

存储配置文件

### .env

存储API的文件

`API_KEY = <put your api key here>`

### models.json

存储模型其他信息的文件

### cfg.json

存储用户配置信息

## log

日志目录

## memory

用户画像（历史学习情况信息）存储路径