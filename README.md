\# 🧠 DocuMind — Enterprise RAG-Based AI Knowledge Assistant



An AI-powered document question-answering system that allows users to interact with organizational documents using natural language. Built with \*\*Retrieval-Augmented Generation (RAG)\*\*, semantic search, vector embeddings, and Large Language Models (LLMs).



🔗 \*\*Live Demo:\*\* \[DocuMind](https://documind-alq.pages.dev/)



⚙️ \*\*Backend Health:\*\* \[API Health Check](https://documind-api-uu9t.onrender.com/api/health)



\---



\## 📌 Overview



DocuMind is an AI-powered knowledge assistant designed to retrieve relevant information from uploaded or indexed documents and generate context-aware answers.



Instead of manually searching through lengthy documents, users can ask questions in natural language and receive relevant answers supported by document-based source citations.



The system uses a Retrieval-Augmented Generation (RAG) pipeline to improve response relevance and reduce unsupported answers.



\### ✨ Key Features



\- 📄 \*\*Document Processing:\*\* Extracts and processes text from PDF documents.

\- 🔍 \*\*Semantic Search:\*\* Retrieves relevant document content using vector embeddings.

\- 🧠 \*\*RAG Pipeline:\*\* Combines document retrieval with LLM-based answer generation.

\- 💬 \*\*Natural Language Q\&A:\*\* Allows users to ask questions about indexed documents.

\- 📚 \*\*Source Citations:\*\* Provides document references to support generated answers.

\- 🛡️ \*\*Grounded Responses:\*\* Uses retrieval relevance checks to avoid answering unsupported questions.

\- ⚡ \*\*Vector Similarity Search:\*\* Uses FAISS for efficient similarity-based retrieval.

\- 🔄 \*\*Conversation Management:\*\* Supports creating chat sessions.

\- 🚀 \*\*Cloud Deployment:\*\* Frontend and backend deployed independently.



\---



\## 🛠️ Tech Stack



| Category | Technologies |

|---|---|

| Frontend | React.js, Vite, JavaScript |

| Backend | Python, FastAPI |

| AI / LLM | Groq API, GPT-OSS 120B |

| Embeddings | FastEmbed, BAAI/bge-small-en-v1.5 |

| Vector Database | FAISS |

| Document Processing | PyPDF |

| Database / ORM | SQLite, SQLAlchemy |

| Data Validation | Pydantic |

| Deployment | Cloudflare Pages, Render |

| Version Control | Git, GitHub |



\---



\## 🏗️ System Architecture



```mermaid

flowchart TD

&#x20;   A\[User] --> B\[React Frontend]

&#x20;   B --> C\[FastAPI Backend]

&#x20;   C --> D\[User Query]

&#x20;   D --> E\[Embedding Model]

&#x20;   E --> F\[FAISS Vector Search]

&#x20;   F --> G\[Relevant Document Chunks]

&#x20;   G --> H\[Context and Prompt Construction]

&#x20;   H --> I\[Groq LLM API]

&#x20;   I --> J\[Generated Answer]

&#x20;   G --> K\[Source References]

&#x20;   J --> L\[Response with Citations]

&#x20;   K --> L

&#x20;   L --> B

&#x20;   B --> A

```



\---



\## 🔄 RAG Pipeline



DocuMind follows a Retrieval-Augmented Generation workflow:



\*\*1. 📄 Document Loading\*\*



PDF documents are loaded and their text is extracted for further processing.



\*\*2. ✂️ Text Chunking\*\*



Extracted text is divided into smaller chunks to improve retrieval relevance and provide manageable context to the language model.



\*\*3. 🔢 Text Embeddings\*\*



The `BAAI/bge-small-en-v1.5` embedding model converts document chunks into numerical vector representations.



\*\*4. 🗂️ Vector Indexing\*\*



Document embeddings are stored in a FAISS index for similarity-based retrieval.



\*\*5. 🔍 Query Retrieval\*\*



When a user submits a question, the query is converted into an embedding and compared against indexed document vectors.



\*\*6. 🧠 Context-Aware Generation\*\*



Relevant retrieved chunks are passed as context to the Groq-hosted LLM, which generates an answer based on the available information.



\*\*7. 📚 Source Citations\*\*



The response includes references to the retrieved document sources.



\*\*8. 🛡️ Relevance-Based Refusal\*\*



Questions without sufficient supporting document context are handled through retrieval relevance checks rather than generating unsupported answers.



\---



\## 📊 Evaluation



The retrieval system was evaluated using a project-specific question set containing \*\*28 questions\*\*:



\- 23 answerable questions

\- 5 unanswerable questions



\### Baseline Evaluation Results



| Metric | Result |

|---|---:|

| Hit Rate @ 1 | 95.7% |

| Hit Rate @ 3 | 100% |

| Hit Rate @ k | 100% |

| Mean Reciprocal Rank (MRR) | 0.978 |

| Correct Refusal Rate | 100% |

| False Refusal Rate | 0% |

| Average Latency | 7,154.5 ms |



\### ⚙️ Evaluation Configuration



| Parameter | Value |

|---|---|

| Embedding Model | BAAI/bge-small-en-v1.5 |

| Chunk Size | 500 words |

| Chunk Overlap | 80 words |

| Top-k Retrieval | 5 |

| Relevance Threshold | 0.45 |

| Indexed Chunks | 7 |

| LLM Used | Yes |



\*\*Note:\*\* These results represent the current evaluation dataset and document collection. They should not be interpreted as general-purpose accuracy or performance guarantees.



\---



\## 📁 Project Structure



```text

DocuMind/

│

├── backend/

│   ├── app/

│   │   ├── main.py

│   │   ├── api/

│   │   ├── services/

│   │   └── ...

│   │

│   ├── eval/

│   │

│   ├── sample\_docs/

│   │

│   ├── Dockerfile

│   ├── requirements.txt

│   ├── requirements-dev.txt

│   ├── .env.example

│   └── ...

│

├── frontend/

│   ├── src/

│   ├── public/

│   ├── package.json

│   ├── package-lock.json

│   ├── vite.config.js

│   └── .env.example

│

├── render.yaml

└── README.md

```



\---



\## 💻 Local Installation and Setup



Follow these instructions to run DocuMind locally.



\### Prerequisites



\- Python 3.12

\- Node.js and npm

\- Git

\- Groq API key



\### 1. Clone the Repository



```bash

git clone https://github.com/gitbot55/DocuMind-.git

```



Navigate to the project directory:



```bash

cd DocuMind-/documind

```



\### 2. Backend Setup



Navigate to the backend:



```bash

cd backend

```



Create a virtual environment:



```bash

python -m venv .venv

```



Activate it on Windows PowerShell:



```powershell

.venv\\Scripts\\Activate.ps1

```



Install dependencies:



```bash

pip install -r requirements.txt

```



\### 3. Configure Environment Variables



Create a `.env` file inside the backend directory.



Configure the following variables:



```env

GROQ\_API\_KEY=your\_groq\_api\_key

GROQ\_MODEL=openai/gpt-oss-120b

ALLOWED\_ORIGINS=http://localhost:5173

```



Replace `your\_groq\_api\_key` with your own Groq API key.



⚠️ Never commit your actual `.env` file or expose your API key publicly.



\### 4. Run the Backend



Start the FastAPI server:



```bash

uvicorn app.main:app --reload --port 8000

```



Backend address:



```text

http://localhost:8000

```



Health check:



```text

http://localhost:8000/api/health

```



\### 5. Frontend Setup



Open a second terminal and navigate to the frontend:



```bash

cd frontend

```



Install dependencies:



```bash

npm install

```



Create a `.env` file inside the frontend directory:



```env

VITE\_API\_URL=http://localhost:8000

```



\### 6. Run the Frontend



```bash

npm run dev

```



Frontend address:



```text

http://localhost:5173

```



🎉 DocuMind is now running locally.



Keep both the backend and frontend terminals running while using the application.



\---



\## 🌐 Deployment



DocuMind uses separate cloud services for frontend and backend hosting.



\### Frontend — Cloudflare Pages



\- Framework: React + Vite

\- Root Directory: `documind/frontend`

\- Build Command: `npm run build`

\- Output Directory: `dist`

\- Environment Variable:



```env

VITE\_API\_URL=https://documind-api-uu9t.onrender.com

```



\### Backend — Render



\- Runtime: Docker

\- Dockerfile: `./documind/backend/Dockerfile`

\- Docker Context: `./documind/backend`

\- Health Check Path: `/api/health`



Required environment variables:



```env

GROQ\_API\_KEY=your\_groq\_api\_key

GROQ\_MODEL=openai/gpt-oss-120b

ALLOWED\_ORIGINS=https://documind-alq.pages.dev

```



The API key should be configured securely through Render's environment variable settings.



\---



\## 🔌 API Endpoints



The backend exposes REST API endpoints through FastAPI.



| Endpoint | Method | Purpose |

|---|---|---|

| `/api/health` | GET | Backend health check |

| `/api/chat/new` | POST | Create a new chat session |

| `/api/documents` | GET | Retrieve indexed document information |



Additional application routes handle chat interactions and document-related operations.



\---



\## 🧪 Testing and Evaluation



The project includes an evaluation module under:



```text

backend/eval/

```



Run the evaluation script from the backend directory:



```bash

python eval/run\_eval.py

```



The evaluation examines retrieval quality, ranking performance, refusal behavior, and response latency using the project's test questions.



\---



\## ⚠️ Current Limitations



\- Evaluation currently uses a relatively small document collection.

\- Retrieval quality depends on document quality and chunking configuration.

\- LLM response generation depends on external Groq API availability.

\- Initial backend startup may take additional time while the runtime initializes.

\- Evaluation results may vary with document collections, queries, and retrieval settings.



\---



\## 🔮 Future Improvements



\- 📂 Support for additional document formats such as DOCX and TXT.

\- 📈 Expand evaluation datasets and introduce more comprehensive RAG evaluation metrics.

\- 🔍 Improve retrieval through hybrid search and reranking.

\- 🧠 Experiment with alternative embedding models and chunking strategies.

\- 👥 Add multi-user document collections and access control.

\- 📊 Introduce analytics and document usage insights.

\- ⚡ Optimize retrieval and response latency.



\---



\## 👨‍💻 Author



\*\*Yash Kaluskar\*\*



B.Tech Computer Science Engineering



📍 Vadodara, Gujarat, India



🔗 \*\*GitHub:\*\* \[gitbot55](https://github.com/gitbot55)



\---



⭐ If you find this project interesting, consider giving the repository a star!

