import streamlit as st
import time
from src.council import CouncilMember, CouncilOrchestrator, Chairman, get_available_models, PerformanceMetrics
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
    
    # Initialize distributed config in session state if not present
    if 'distributed_members' not in st.session_state:
        st.session_state.distributed_members = [
            {"name": cfg["name"], "api_url": cfg["api_url"], "model": cfg["model"]}
            for cfg in COUNCIL_MEMBERS_CONFIG
        ]
    if 'distributed_chairman' not in st.session_state:
        st.session_state.distributed_chairman = {
            "name": CHAIRMAN_CONFIG["name"],
            "api_url": CHAIRMAN_CONFIG["api_url"],
            "model": CHAIRMAN_CONFIG["model"]
        }
    # --- Help Section ---
    with st.sidebar.expander("📖 How to setup remote machines", expanded=False):
        st.markdown("""
**To use distributed mode, configure each member machine:**

1. **Install Ollama** on each machine
2. **Pull the models** you want to use:
   ```
   ollama pull llama3.2:1b
   ollama pull mistral
   ```
3. **Enable network access** (Ollama listens only to localhost by default):
   
   **Windows (PowerShell):**
   ```powershell
   $env:OLLAMA_HOST = "0.0.0.0"
   ollama serve
   ```
   
   **Mac/Linux:**
   ```bash
   OLLAMA_HOST=0.0.0.0 ollama serve
   ```

4. **Find the machine's IP address:**
   - Windows: `ipconfig`
   - Mac/Linux: `ifconfig` or `ip addr`

5. **Add the member** below with the IP address (e.g., `http://192.168.1.15:11434`)

⚠️ **All machines must be on the same network (LAN)**
        """)
    
    # --- Server URL (common for all) ---
    with st.sidebar.expander("🌐 Server Settings", expanded=False):
        default_url = st.text_input(
            "Default Ollama Server URL",
            value="http://localhost:11434",
            help="This URL will be used when adding new members"
        )
    
    # --- Council Members Editor ---
    with st.sidebar.expander("👥 Council Members", expanded=True):
        members_to_remove = []
        
        for i, member in enumerate(st.session_state.distributed_members):
            st.markdown(f"**Member {i+1}**")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Name
                new_name = st.text_input(
                    "Name", 
                    value=member["name"], 
                    key=f"member_name_{i}",
                    label_visibility="collapsed"
                )
                st.session_state.distributed_members[i]["name"] = new_name
                
                # API URL
                new_url = st.text_input(
                    "API URL",
                    value=member["api_url"],
                    key=f"member_url_{i}",
                    label_visibility="collapsed",
                    placeholder="http://IP:11434"
                )
                st.session_state.distributed_members[i]["api_url"] = new_url
                
                # Model
                new_model = st.text_input(
                    "Model",
                    value=member["model"],
                    key=f"member_model_{i}",
                    label_visibility="collapsed",
                    placeholder="llama3.2:1b"
                )
                st.session_state.distributed_members[i]["model"] = new_model
            
            with col2:
                if st.button("🗑️", key=f"remove_member_{i}", help="Remove this member"):
                    members_to_remove.append(i)
            
            st.markdown("---")
        
        # Remove members marked for deletion
        for idx in sorted(members_to_remove, reverse=True):
            st.session_state.distributed_members.pop(idx)
            st.rerun()
        
        # Add new member button
        if st.button("➕ Add Member"):
            st.session_state.distributed_members.append({
                "name": f"Member_{len(st.session_state.distributed_members) + 1}",
                "api_url": default_url,
                "model": "llama3.2:1b"
            })
            st.rerun()
    
    # --- Chairman Editor ---
    with st.sidebar.expander("👑 Chairman", expanded=True):
        chairman = st.session_state.distributed_chairman
        
        chairman["name"] = st.text_input(
            "Chairman Name",
            value=chairman["name"],
            key="chairman_name"
        )
        
        chairman["api_url"] = st.text_input(
            "Chairman API URL",
            value=chairman["api_url"],
            key="chairman_url"
        )
        
        chairman["model"] = st.text_input(
            "Chairman Model",
            value=chairman["model"],
            key="chairman_model"
        )
    
    # --- Initialize Button ---
    if st.sidebar.button("🚀 Initialize Distributed Council"):
        if len(st.session_state.distributed_members) < 2:
            st.sidebar.warning("Please add at least 2 council members.")
        else:
            with st.spinner("Connecting to nodes..."):
                members = [
                    CouncilMember(name=cfg["name"], base_url=cfg["api_url"], model=cfg["model"])
                    for cfg in st.session_state.distributed_members
                ]
                chairman = Chairman(
                    name=st.session_state.distributed_chairman["name"],
                    base_url=st.session_state.distributed_chairman["api_url"],
                    model=st.session_state.distributed_chairman["model"]
                )
                orch = CouncilOrchestrator(members, chairman)
                st.session_state.orchestrator = orch
                st.session_state.health_status = orch.check_health()
                st.rerun()

# --- Status Display & Performance Dashboard ---
if st.session_state.orchestrator:
    orch = st.session_state.orchestrator
    health = st.session_state.health_status
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Performance Dashboard")
    
    # Chairman Status with metrics
    chairman_metrics = orch.chairman.metrics
    chairman_online = health.get(orch.chairman.name, False)
    
    with st.sidebar.container():
        if chairman_online:
            st.sidebar.success(f"🎓 **Chairman** ({chairman_metrics.model})")
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("Ping", f"{chairman_metrics.last_ping_ms:.0f}ms")
            with col2:
                st.metric("Status", "🟢 Online")
        else:
            st.sidebar.error(f"🎓 **Chairman** ({chairman_metrics.model}): Offline")
    
    st.sidebar.markdown("---")
    st.sidebar.write("**Council Members:**")
    
    for member in orch.members:
        status = health.get(member.name, False)
        metrics = member.metrics
        
        # Status indicator with color
        status_color = "🟢" if status else "🔴"
        status_text = metrics.status.capitalize()
        
        with st.sidebar.expander(f"{status_color} {member.name}", expanded=False):
            # Status row
            st.write(f"**Model:** `{metrics.model}`")
            st.write(f"**Status:** {status_text}")
            
            # Metrics in columns
            if metrics.last_ping_ms > 0:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Last Ping", f"{metrics.last_ping_ms:.0f}ms")
                with col2:
                    if metrics.avg_latency_ms > 0:
                        st.metric("Avg Response", f"{metrics.avg_latency_ms:.0f}ms")
                    else:
                        st.metric("Avg Response", "N/A")
            
            # Success rate if there have been requests
            if metrics.total_requests > 0:
                st.progress(metrics.success_rate / 100)
                st.caption(f"Success Rate: {metrics.success_rate:.0f}% ({metrics.successful_requests}/{metrics.total_requests})")

    # Filter active members for execution
    active_members = [m for m in orch.members if health.get(m.name, False)]
    orch.members = active_members
    
    # Refresh button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Status"):
        st.session_state.health_status = orch.check_health()
        st.rerun()

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
                start_time = time.time()
                with st.spinner("Council members are thinking..."):
                    opinions = orch.gather_opinions(query)
                stage1_time = (time.time() - start_time) * 1000
                
                if not opinions:
                    st.error("Failed to gather opinions.")
                    st.stop()
                
                # Stage 1 Performance Summary
                st.caption(f"⏱️ Stage 1 completed in {stage1_time:.0f}ms")
                
                # Display Opinions in Tabs with latency info
                tab_names = [f"{op.member_name} ({op.latency_ms:.0f}ms)" for op in opinions]
                tabs = st.tabs(tab_names)
                for i, tab in enumerate(tabs):
                    with tab:
                        # Latency indicator
                        latency = opinions[i].latency_ms
                        if latency < 5000:
                            latency_color = "🟢"
                        elif latency < 15000:
                            latency_color = "🟡"
                        else:
                            latency_color = "🔴"
                        
                        col1, col2 = st.columns([4, 1])
                        with col2:
                            st.metric("Response Time", f"{latency:.1f}s" if latency > 1000 else f"{latency:.0f}ms")
                        
                        st.markdown(opinions[i].content)

            # Stage 2: Peer Review
            with progress_container:
                st.subheader("Stage 2: Peer Review & Ranking")
                start_time = time.time()
                with st.spinner("Members are reviewing each other..."):
                    reviewed_opinions = orch.peer_review(query, opinions)
                stage2_time = (time.time() - start_time) * 1000
                
                st.caption(f"⏱️ Stage 2 completed in {stage2_time:.0f}ms")
                
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
                start_time = time.time()
                with st.spinner("The Chairman is synthesizing the final answer..."):
                    final_answer, chairman_latency = orch.chairman.synthesize(query, reviewed_opinions)
                stage3_time = (time.time() - start_time) * 1000
                
                st.success("Final Answer Generated")
                
                # Performance summary
                total_time = stage1_time + stage2_time + stage3_time
                
                st.markdown("---")
                st.markdown("### 📊 Performance Summary")
                perf_cols = st.columns(4)
                with perf_cols[0]:
                    st.metric("Stage 1", f"{stage1_time/1000:.1f}s")
                with perf_cols[1]:
                    st.metric("Stage 2", f"{stage2_time/1000:.1f}s")
                with perf_cols[2]:
                    st.metric("Stage 3", f"{chairman_latency/1000:.1f}s")
                with perf_cols[3]:
                    st.metric("Total", f"{total_time/1000:.1f}s", delta=f"{len(opinions)} opinions")
                
                st.markdown("---")
                st.markdown("### 🎓 Chairman's Synthesis")
                st.markdown(final_answer)
                
            # Update health status to refresh metrics
            st.session_state.health_status = orch.check_health()

else:
    st.info("👈 Please initialize the council using the sidebar to start.")
