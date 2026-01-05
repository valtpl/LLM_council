import streamlit as st
import time
from src.council import CouncilMember, CouncilOrchestrator, Chairman, get_available_models
from config import COUNCIL_MEMBERS_CONFIG, CHAIRMAN_CONFIG

st.set_page_config(page_title="Local LLM Council", layout="wide")

st.title("🏛️ Local LLM Council")
st.markdown("""
This system uses a distributed council of local LLMs to answer your queries.
1. **Opinions**: Multiple models generate initial answers.
2. **Peer Review**: Models review and rank each other's answers.
3. **Chairman Synthesis**: A designated Chairman model synthesizes the final result.
""")

# Sidebar Configuration
st.sidebar.header("Setup & Configuration")

# Initialize Session State
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None
if 'health_status' not in st.session_state:
    st.session_state.health_status = {}

# --- Deployment Mode Selection ---
deployment_mode = st.sidebar.radio(
    "Deployment Mode",
    ["Local (Single Machine)", "Distributed (Network)"],
    help="Choose 'Local' to run everything on this machine using one Ollama instance. Choose 'Distributed' to use the IPs defined in config.py."
)

def initialize_local_council(council_models, chairman_model):
    members = []
    # Create members with unique names even if models are same
    for i, model in enumerate(council_models):
        members.append(CouncilMember(name=f"Member_{i+1} ({model})", base_url="http://localhost:11434", model=model))
    
    chairman = Chairman(name=f"Chairman ({chairman_model})", base_url="http://localhost:11434", model=chairman_model)
    return CouncilOrchestrator(members, chairman)

def initialize_distributed_council():
    members = [
        CouncilMember(name=cfg["name"], base_url=cfg["api_url"], model=cfg["model"])
        for cfg in COUNCIL_MEMBERS_CONFIG
    ]
    chairman = Chairman(name=CHAIRMAN_CONFIG["name"], base_url=CHAIRMAN_CONFIG["api_url"], model=CHAIRMAN_CONFIG["model"])
    return CouncilOrchestrator(members, chairman)

# --- Configuration UI ---
if deployment_mode == "Local (Single Machine)":
    st.sidebar.subheader("Local Configuration")
    available_models = get_available_models()
    
    if not available_models:
        st.sidebar.error("⚠️ Could not connect to Ollama at http://localhost:11434. Is it running?")
        if st.sidebar.button("Retry Connection"):
            st.rerun()
    else:
        st.sidebar.success(f"Found {len(available_models)} models.")
        
        # Default selection logic
        default_council = available_models[:3] if len(available_models) >= 3 else available_models
        
        selected_council_models = st.sidebar.multiselect(
            "Select Council Members (at least 2)",
            available_models,
            default=default_council
        )
        
        selected_chairman_model = st.sidebar.selectbox(
            "Select Chairman Model",
            available_models,
            index=0
        )
        
        if st.sidebar.button("Initialize Local Council"):
            if len(selected_council_models) < 2:
                st.sidebar.warning("Please select at least 2 council members.")
            else:
                with st.spinner("Initializing..."):
                    orch = initialize_local_council(selected_council_models, selected_chairman_model)
                    st.session_state.orchestrator = orch
                    st.session_state.health_status = orch.check_health()
                    st.rerun()

else: # Distributed
    st.sidebar.subheader("Network Configuration")
    st.sidebar.info("Using configuration from `config.py`")
    
    # Show config preview
    with st.sidebar.expander("View Config"):
        st.write("Council Members:")
        st.json(COUNCIL_MEMBERS_CONFIG)
        st.write("Chairman:")
        st.json(CHAIRMAN_CONFIG)
        
    if st.sidebar.button("Initialize Distributed Council"):
        with st.spinner("Connecting to nodes..."):
            orch = initialize_distributed_council()
            st.session_state.orchestrator = orch
            st.session_state.health_status = orch.check_health()
            st.rerun()

# --- Status Display ---
if st.session_state.orchestrator:
    orch = st.session_state.orchestrator
    health = st.session_state.health_status
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")
    
    if health.get(orch.chairman.name, False):
        st.sidebar.success(f"🎓 {orch.chairman.name}: Online")
    else:
        st.sidebar.error(f"🎓 {orch.chairman.name}: Offline")
        
    st.sidebar.write("Council Members:")
    for member in orch.members:
        status = health.get(member.name, False)
        icon = "🟢" if status else "🔴"
        st.sidebar.write(f"{icon} {member.name}")

    # Filter active members for execution
    active_members = [m for m in orch.members if health.get(m.name, False)]
    orch.members = active_members

# --- Main Application Logic ---
if st.session_state.orchestrator:
    orch = st.session_state.orchestrator
    
    # Main Query Interface
    query = st.text_area("Enter your query:", height=100)
    
    if st.button("Ask the Council"):
        if not query:
            st.warning("Please enter a query.")
        elif not orch.members:
            st.error("No active council members found. Please check your configuration and connections.")
        elif not st.session_state.health_status.get(orch.chairman.name, False):
             st.error("Chairman is offline. Cannot proceed.")
        else:
            # Progress Container
            progress_container = st.container()
            
            # Stage 1: Opinions
            with progress_container:
                st.subheader("Stage 1: Gathering Opinions")
                with st.spinner("Council members are thinking..."):
                    opinions = orch.gather_opinions(query)
                
                if not opinions:
                    st.error("Failed to gather opinions.")
                    st.stop()
                
                # Display Opinions in Tabs
                tabs = st.tabs([op.member_name for op in opinions])
                for i, tab in enumerate(tabs):
                    with tab:
                        st.markdown(opinions[i].content)

            # Stage 2: Peer Review
            with progress_container:
                st.subheader("Stage 2: Peer Review & Ranking")
                with st.spinner("Members are reviewing each other..."):
                    reviewed_opinions = orch.peer_review(query, opinions)
                
                with st.expander("View Peer Reviews"):
                    for op in reviewed_opinions:
                        st.markdown(f"### Reviews for {op.member_name}'s Answer")
                        if op.reviews:
                            for rev in op.reviews:
                                st.info(rev)
                        else:
                            st.write("No reviews received.")

            # Stage 3: Chairman Synthesis
            with progress_container:
                st.subheader("Stage 3: Chairman's Final Verdict")
                with st.spinner("The Chairman is synthesizing the final answer..."):
                    final_answer = orch.chairman.synthesize(query, reviewed_opinions)
                
                st.success("Final Answer Generated")
                st.markdown("### 🎓 Chairman's Synthesis")
                st.markdown(final_answer)

else:
    st.info("👈 Please initialize the council using the sidebar to start.")
