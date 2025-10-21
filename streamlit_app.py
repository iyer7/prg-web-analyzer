import streamlit as st
import os
import web_analyzer_logic as logic  # Import our NEW logic file
import configparser
import shutil  # For cleaning up temp files

# --- 1. Page Configuration ---
st.set_page_config(page_title="Aerosol Jet Analyzer", layout="wide")
st.title("Aerosol Jet .prg Analyzer 🚀")
st.write("Upload a .prg file and set the G-Factor to analyze its mechanical stress points and generate an animation.")

# --- 2. Configuration & Temp Folder Setup ---
# Create a temporary directory for this user's session
TEMP_DIR = "temp_files"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Use Streamlit's session state to "remember" the g-factor
if 'g_factor' not in st.session_state:
    config = configparser.ConfigParser()
    config_path = logic.get_config_path()
    if os.path.exists(config_path):
        config.read(config_path)
        st.session_state.g_factor = config.getfloat('Parameters', 'g_factor', fallback=0.5)
    else:
        st.session_state.g_factor = 0.5

# --- 3. Sidebar (for inputs) ---
with st.sidebar:
    st.header("Analysis Parameters")
    uploaded_file = st.file_uploader("Upload your .prg file", type=["prg"])

    g_factor_input = st.number_input(
        "Enter G-Factor (e.g., 0.5):",
        min_value=0.01,
        value=st.session_state.g_factor,
        step=0.1
    )
    run_button = st.button("Run Analysis", type="primary")

# --- 4. Main Page (for results) ---
if run_button:
    # Save the new g_factor for next time
    if g_factor_input != st.session_state.g_factor:
        st.session_state.g_factor = g_factor_input
        config = configparser.ConfigParser()
        config_path = logic.get_config_path()
        config['Parameters'] = {'g_factor': str(st.session_state.g_factor)}
        with open(config_path, 'w') as configfile:
            config.write(configfile)

    if uploaded_file is not None:
        # Save the uploaded file to the temporary path
        temp_filepath = os.path.join(TEMP_DIR, uploaded_file.name)
        with open(temp_filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Show a spinner while working
        with st.spinner("Running analysis and rendering animation... This may take a moment."):
            try:
                # --- Run Analysis ---
                parsed_segments = logic.parse_prg_file(temp_filepath)
                if not parsed_segments:
                    st.warning("Could not parse any segments for analysis.")
                else:
                    lim_speed, stress, arc_info, lim_arc = logic.run_path_stress_analysis(
                        parsed_segments, st.session_state.g_factor
                    )

                    # --- Display Report ---
                    st.subheader("Analysis Report")
                    report_string = logic.generate_analysis_report(lim_speed, stress, st.session_state.g_factor,
                                                                   lim_arc)
                    st.code(report_string, language="text")

                    # --- Create & Display Download Button ---
                    base, ext = os.path.splitext(uploaded_file.name)
                    annotated_filename = f"{base}_annotated{ext}"
                    annotated_filepath = os.path.join(TEMP_DIR, annotated_filename)

                    logic.create_annotated_prg_file(
                        temp_filepath, annotated_filepath, lim_speed, stress,
                        arc_info, st.session_state.g_factor, lim_arc
                    )

                    with open(annotated_filepath, "r") as f:
                        st.download_button(
                            label="Download Annotated .prg File",
                            data=f.read(),
                            file_name=annotated_filename,
                            mime="text/plain"
                        )

                    # --- Create & Display Animation ---
                    st.subheader("Toolpath Animation")
                    video_save_path = os.path.join(TEMP_DIR, "animation.mp4")

                    animation_path = logic.animate_printer(
                        temp_filepath, lim_speed, video_save_path
                    )

                    if animation_path:
                        video_file = open(animation_path, 'rb')
                        video_bytes = video_file.read()
                        st.video(video_bytes)
                        video_file.close()
                    else:
                        st.info("No segments were found to animate.")

                    st.success("Analysis complete!")

            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")
                st.error("Please check the .prg file format or contact support.")

        # Clean up the temporary files for this session
        shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR)  # Re-create it for the next run

    else:
        st.error("Please upload a .prg file first.")