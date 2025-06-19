
# 🌱 BR-MANGUE: Modelo de Predição para Áreas de Manguezais

Este repositório contém o código e os dados necessários para executar uma aplicação baseada em [Streamlit](https://streamlit.io/), com o objetivo de simular os impactos da elevação do nível do mar em manguezais, com base no modelo BR-MANGUE.

---

## ✅ O que você vai encontrar aqui

- Código do modelo BR-MANGUE atualizado para Python
- Interface web interativa com [Streamlit](https://streamlit.io/)
- Execução remota e simples via Google Colab
- Visualização dos resultados via URL pública (ngrok)

---

## 🚀 Como Rodar o Projeto no Google Colab

Você pode testar a aplicação diretamente no navegador, sem instalar nada no seu computador. Siga os passos abaixo:

---

### 1. Crie uma conta no GitHub

Se ainda não tem, registre-se em:  
👉 [https://github.com/join](https://github.com/join)

---

### 2. Gere um Personal Access Token (PAT) no GitHub

Para clonar este repositório via notebook, você precisará de um token de acesso pessoal:

1. Acesse: [https://github.com/settings/tokens/new](https://github.com/settings/tokens/new)
2. Dê um nome (ex: `colab-access`)
3. Marque a opção **repo**
4. Clique em **"Generate token"**
5. Copie o token gerado (você só verá uma vez!)

---

### 3. Crie uma conta no ngrok

O ngrok será usado para criar uma URL pública para a aplicação:

1. Acesse: [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
2. Após criar sua conta, vá para:  
   👉 [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
3. Copie seu **authtoken pessoal**

---

### 4. Execute o Notebook no Google Colab

Abra o notebook clicando no link abaixo:

📎 [Abrir notebook no Google Colab](https://colab.research.google.com/drive/1PDYaIL17XaQaYzzYOUc_RyKqDsSAWhWW?usp=sharing)

Você será solicitado a informar:

- Seu **nome de usuário do GitHub**
- Seu **Personal Access Token (PAT)** do GitHub
- Seu **authtoken** do ngrok

---

### 5. Acesse a Interface do Modelo

Ao final da execução, o notebook exibirá uma URL pública gerada pelo ngrok. Clique nessa URL para abrir a aplicação Streamlit no navegador e explorar o modelo BR-MANGUE.

---

## 📁 Estrutura do Projeto

```
br_mangue_model/
├── streamlit_app.py        # Interface principal
├── data/                   # Dados de entrada (raster, shapefiles, etc.)
├── model/                  # Funções do modelo BR-MANGUE
├── utils/                  # Funções auxiliares
└── README.md               # Instruções de uso
```

---

## 💡 Sobre o Projeto

Este projeto é parte de uma pesquisa de mestrado voltada para análise geoespacial de áreas costeiras ameaçadas pela elevação do nível do mar. O modelo BR-MANGUE foi adaptado para rodar de forma interativa e visual, facilitando a análise de cenários futuros em regiões de manguezal.

---

## 👨‍💻 Autor

**Felipe Martins Sousa**  
Mestrando em Ciência e Tecnologia Ambiental (UFMA)  
📧 Contato: pep.ocean@icloud.com

---

## 📄 Licença

Este projeto está sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais informações.
