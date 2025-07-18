
## 📚 Adaptive Learning Platform – Backend

A FastAPI backend using Google OAuth2 authentication, PostgreSQL (Neon), and MinIO for file storage.
Document conversion (e.g., PPTX to PDF) is handled using LibreOffice in headless mode.
Project dependencies are managed using [`uv`](https://github.com/astral-sh/uv).

---

## ⚙️ Project Setup

### 1. 🧪 Clone the Repository

```bash
git clone https://github.com/abdullah270602/Adaptive-E-Learning-Platform-Bakend
cd Adaptive-E-Learning-Platform-Bakend
```

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

---

### 3. 🔧 LibreOffice Installation (Required for Document Conversion)

Document conversion (e.g., `.pptx` to `.pdf`) uses LibreOffice in headless mode.

#### 🔸 **Linux (Ubuntu/Debian)**

```bash
sudo apt update
sudo apt install libreoffice -y
```

Verify installation:

```bash
libreoffice --version
```

#### 🔸 **Windows**

1. Download LibreOffice from: [https://www.libreoffice.org/download/download/](https://www.libreoffice.org/download/download/)
2. Install it normally.
3. Add the `program` folder (e.g., `C:\Program Files\LibreOffice\program`) to your **System Environment PATH**.
4. Use `soffice.com` or `soffice.exe` for CLI operations.

Verify in CMD:

```bash
soffice.com --version
```

> ⚠️ On Windows, the correct CLI binary is usually `soffice.com`, not `libreoffice`.

---

### 4. 🔐 Environment Variables (`.env`)

Create a `.env` file in the root directory and configure required environment variables.
(See `.env.example` for reference.)

---

### 5. 🚀 Run the Application

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

