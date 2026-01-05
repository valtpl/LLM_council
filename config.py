# Configuration for the Council Members

# Define your local Ollama instances here.
# If running on the same machine, they might be on different ports if you are using something like docker-compose,
# or if they are on different machines on the LAN, use their IP addresses.

COUNCIL_MEMBERS_CONFIG = [
    {
        "name": "Member_1",
        "api_url": "http://localhost:11434",
        "model": "llama3"
    },
    {
        "name": "Member_2",
        "api_url": "http://localhost:11434", # Replace with actual IP if distributed
        "model": "mistral"
    },
    {
        "name": "Member_3",
        "api_url": "http://localhost:11434", # Replace with actual IP if distributed
        "model": "phi3"
    }
]

CHAIRMAN_CONFIG = {
    "name": "Chairman",
    "api_url": "http://localhost:11434", # Should be on a separate machine/process ideally
    "model": "llama3"
}
