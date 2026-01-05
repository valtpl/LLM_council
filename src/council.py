import requests
from typing import List, Dict, Optional
import concurrent.futures
import time
from dataclasses import dataclass, field

def get_available_models(base_url: str = "http://localhost:11434") -> List[str]:
    """Fetches the list of available models from an Ollama instance."""
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
    except requests.RequestException:
        pass
    return []

@dataclass
class Opinion:
    member_name: str
    content: str
    score: float = 0.0
    reviews: List[str] = field(default_factory=list)

class CouncilMember:
    def __init__(self, name: str, base_url: str, model: str):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = 120  # Increased timeout for longer generations

    def is_alive(self) -> bool:
        """Check if the Ollama instance is reachable."""
        try:
            # Ollama usually has a root endpoint or /api/tags
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def generate(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Generates a response from the local Ollama instance."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.RequestException as e:
            print(f"Error communicating with {self.name} ({self.base_url}): {e}")
            return None

class Chairman(CouncilMember):
    def synthesize(self, query: str, opinions: List[Opinion]) -> str:
        """Stage 3: Synthesize all opinions and reviews into a final answer."""
        
        # Construct the context from all opinions and their reviews
        context = ""
        for i, op in enumerate(opinions):
            context += f"\n--- Opinion {i+1} (from {op.member_name}) ---\n"
            context += f"{op.content}\n"
            if op.reviews:
                context += "  Peer Reviews:\n"
                for rev in op.reviews:
                    context += f"  - {rev}\n"
        
        prompt = f"""
        You are the Chairman of an AI Council. 
        
        Original User Query: "{query}"
        
        Here are the opinions provided by the council members, along with peer reviews:
        {context}
        
        Your task:
        1. Analyze the different perspectives provided.
        2. Weigh the arguments based on the peer reviews and your own judgment.
        3. Synthesize a single, comprehensive, and accurate final answer to the user's query.
        4. Do not explicitly mention "Member 1" or "Member 2" in the final output unless necessary for contrast. Focus on the content.
        
        Final Answer:
        """
        
        return self.generate(prompt, system_prompt="You are a wise and judicious Chairman synthesizing multiple expert opinions.") or "Failed to generate synthesis."

class CouncilOrchestrator:
    def __init__(self, members: List[CouncilMember], chairman: Chairman):
        self.members = members
        self.chairman = chairman

    def check_health(self) -> Dict[str, bool]:
        """Pings all members and chairman to check availability."""
        results = {}
        all_nodes = self.members + [self.chairman]
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_node = {executor.submit(n.is_alive): n for n in all_nodes}
            for future in concurrent.futures.as_completed(future_to_node):
                node = future_to_node[future]
                try:
                    results[node.name] = future.result()
                except Exception:
                    results[node.name] = False
        return results

    def gather_opinions(self, query: str) -> List[Opinion]:
        """Stage 1: Ask all members for their initial opinion."""
        opinions = []
        
        def ask_member(member: CouncilMember):
            response = member.generate(query, system_prompt="You are a helpful expert assistant. Provide a concise and accurate answer.")
            if response:
                return Opinion(member_name=member.name, content=response)
            return None

        print(f"--- Stage 1: Gathering Opinions on '{query}' ---")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_member = {executor.submit(ask_member, m): m for m in self.members}
            for future in concurrent.futures.as_completed(future_to_member):
                result = future.result()
                if result:
                    opinions.append(result)
        
        return opinions

    def peer_review(self, query: str, opinions: List[Opinion]) -> List[Opinion]:
        """Stage 2: Members review each other's answers anonymously."""
        print("--- Stage 2: Peer Review ---")
        
        if len(opinions) < 2:
            print("Not enough opinions for peer review.")
            return opinions

        review_tasks = []
        
        # Each member reviews ALL other opinions
        for reviewer in self.members:
            # Filter out opinions written by the reviewer (if they are in the opinions list)
            # Note: In a distributed system, 'reviewer' object is distinct. We match by name.
            others_opinions = [op for op in opinions if op.member_name != reviewer.name]
            
            if not others_opinions:
                continue

            # We can either ask them to rank all, or review one by one. 
            # To save context window and complexity, let's have them review the set and provide a ranking.
            
            candidates_text = ""
            for i, op in enumerate(others_opinions):
                candidates_text += f"\n[Candidate Answer {i+1}]\n{op.content}\n"

            prompt = f"""
            Original Query: {query}
            
            Here are {len(others_opinions)} answers from other council members:
            {candidates_text}
            
            Task:
            1. Evaluate each candidate answer based on accuracy and insight.
            2. Rank them from best to worst.
            3. Provide a brief critique for each.
            
            Format your response as:
            Rank 1: [Candidate Answer X] - [Critique]
            Rank 2: [Candidate Answer Y] - [Critique]
            ...
            """
            
            review_tasks.append((reviewer, prompt))

        def perform_review(task):
            reviewer, prompt = task
            review_text = reviewer.generate(prompt, system_prompt="You are a critical peer reviewer. Be objective.")
            return (reviewer.name, review_text)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(perform_review, t) for t in review_tasks]
            for future in concurrent.futures.as_completed(futures):
                reviewer_name, review_text = future.result()
                if review_text:
                    # Attach this review to the opinions. 
                    # Since the review text contains rankings for multiple opinions, 
                    # we'll just attach the full review text to the *first* opinion or handle it differently.
                    # A better way for the Chairman to see it is to attach it to the opinions or just pass it to Stage 3.
                    # For simplicity in this data structure, let's append the review to ALL opinions involved, 
                    # or better, let's just store it in the Opinion objects? 
                    # Actually, the Opinion object stores reviews *received*.
                    
                    # We need to parse "Candidate Answer X" back to the specific opinion.
                    # This is brittle with LLMs. 
                    # Alternative: Just append the reviewer's full analysis to every opinion's 'reviews' list 
                    # so the Chairman sees it.
                    
                    for op in opinions:
                        if op.member_name != reviewer_name:
                            op.reviews.append(f"Review by {reviewer_name}:\n{review_text}")
        
        return opinions

    def run_council(self, query: str) -> Dict:
        """Executes the full 3-stage workflow."""
        
        # Stage 1
        opinions = self.gather_opinions(query)
        if not opinions:
            return {"error": "No opinions gathered."}

        # Stage 2
        reviewed_opinions = self.peer_review(query, opinions)

        # Stage 3
        final_answer = self.chairman.synthesize(query, reviewed_opinions)

        return {
            "opinions": reviewed_opinions,
            "final_answer": final_answer
        }
