# Configuration for the Council Members

# CHANGE THIS IF THE OLLAMA SERVER IS ON ANOTHER MACHINE
# If you are running the Streamlit app on one PC but the models are on another PC (Server),
# set this to the Server's IP address. e.g., "http://192.168.1.15:11434"
# If everything is on the same machine, keep it as "http://localhost:11434"
OLLAMA_SERVER_URL = "http://localhost:11434"

COUNCIL_MEMBERS_CONFIG = [
    {
        "name": "Member_1",
        "api_url": OLLAMA_SERVER_URL,
        "model": "llama3"
    },
    {
        "name": "Member_2",
        "api_url": OLLAMA_SERVER_URL,
        "model": "mistral"
    },
    {
        "name": "Member_3",
        "api_url": OLLAMA_SERVER_URL, 
        "model": "phi3"
    }
]

CHAIRMAN_CONFIG = {
    "name": "Chairman",
    "api_url": OLLAMA_SERVER_URL, 
    "model": "llama3"
}
