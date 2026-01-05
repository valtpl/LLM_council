# Local LLM Council

A distributed multi-LLM system where multiple local models collaborate to answer queries, review each other's work, and synthesize a final answer via a Chairman model. Inspired by Andrej Karpathy's LLM Council concept.

## Team Information
*   **TD Group:** CDOF4
*   **Members:**
    *   Héloise ROMEO
    *   Valentin TEMPLE
    *   Théo RENOIR

## Project Overview
This application orchestrates a council of Local LLMs (via Ollama) to provide high-quality answers through a 3-stage process:
1.  **Opinions:** Multiple models generate independent answers to a user query.
2.  **Peer Review:** Models anonymously review and rank each other's answers for accuracy and insight.
3.  **Synthesis:** A designated "Chairman" model analyzes the opinions and reviews to generate a final, comprehensive verdict.

## Setup & Installation

### Prerequisites
*   **Python 3.8+**
*   **Ollama** installed and running on all participating machines.
*   Pull the necessary models (e.g., `llama3`, `mistral`, `phi3`):
    ```bash
    ollama pull llama3
    ollama pull mistral
    ```

### 1. Create a Virtual Environment
It is recommended to use a virtual environment to manage dependencies.

**Windows (PowerShell):**
```powershell
# Create the virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1
# If you get a permission error, run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

## How to Run

### Option A: Local Mode (Single Machine)
Run the entire council on one computer. This is great for testing or if you have a powerful machine.

1.  Ensure Ollama is running (`ollama serve` or via the tray icon).
2.  Start the app:
    ```bash
    streamlit run app.py
    ```
3.  In the sidebar, select **Deployment Mode: Local (Single Machine)**.
4.  Select the models you want to use for the Council and the Chairman.
5.  Click **Initialize Local Council**.

### Option B: Distributed Mode (Multiple Machines)
Run the council across multiple computers on the same network (LAN).

#### 1. Configure Member Machines
By default, Ollama only listens to `localhost`. You must enable it to listen to the network on every machine that will act as a Council Member.

**On each Member Machine:**
1.  Stop Ollama if it is running.
2.  Open a terminal and run:
    **Windows (PowerShell):**
    ```powershell
    $env:OLLAMA_HOST = "0.0.0.0"
    ollama serve
    ```
    **Mac/Linux:**
    ```bash
    OLLAMA_HOST=0.0.0.0 ollama serve
    ```
3.  Find the machine's Local IP address (e.g., `ipconfig` on Windows or `ifconfig` on Mac/Linux).

#### 2. Configure the Chairman (Orchestrator)
On the main machine where you will run the Streamlit app:

1.  Open `config.py`.
2.  Update `COUNCIL_MEMBERS_CONFIG` with the IP addresses and models of your member machines.
    ```python
    COUNCIL_MEMBERS_CONFIG = [
        {
            "name": "Alex's Laptop",
            "api_url": "http://192.168.1.15:11434", # IP of Member 1
            "model": "llama3"
        },
        {
            "name": "Desktop PC",
            "api_url": "http://192.168.1.20:11434", # IP of Member 2
            "model": "mistral"
        }
    ]
    ```

#### 3. Run the App
1.  Start the app on the Chairman machine:
    ```bash
    streamlit run app.py
    ```
2.  In the sidebar, select **Deployment Mode: Distributed (Network)**.
3.  Click **Initialize Distributed Council**.

## Generative AI Usage Statement
*   **Tools Used:** GitHub Copilot / Gemini
*   **Purpose:** Used for code scaffolding, refactoring the orchestrator logic, and generating the Streamlit UI structure.
