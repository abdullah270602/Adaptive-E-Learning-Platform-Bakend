
## 📚 Adaptive Learning Platform – Backend

A FastAPI backend using Google OAuth2 authentication, PostgreSQL (Neon), and MinIO for file storage.
Project dependencies are managed using [`uv`](https://github.com/astral-sh/uv), with optional support for `pip`.

---

## ⚙️ Project Setup

### 1. 🧪 Clone the Repository

```bash
git clone https://github.com/abdullah270602/fyp_backend.git
cd fyp_backend
```

---

Great! Here's a cleaned-up and properly formatted version of that section, ready to paste into your `README.md`:

---

### 2. 🟣 Setup with `uv` (Recommended)

#### Prerequisite: Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Create virtual environment & install dependencies

```bash
uv venv
```

#### Activate the virtual environment

* 🔹 **Linux/macOS**:

  ```bash
  source .venv/bin/activate
  ```

* 🔹 **Windows (CMD or PowerShell)**:

  ```bash
  .venv\Scripts\activate
  ```

> ⚠️ The `.venv` folder is created by default with `uv venv`.

#### Install project dependencies

```bash
uv sync
```
or 

```bash
uv install
```

---

### 3. 🔐 Environment Variables (`.env`)

Create a `.env` file in the root directory setup env vars

### 4. 🚀 Run the Application

```bash
uvicorn main:app --reload
```
---

### 6. 🔍 API Docs

Once the server is running, open:

```
http://127.0.0.1:8000/docs
```

to view the interactive Swagger UI.

---
