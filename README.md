# 🚀 Aerosol Jet .prg Analyzer

**A web-based tool for analyzing Aerosol Jet Printer (.prg) files to identify mechanical stress points and calculate the maximum safe printing speed.**

This tool is designed for technicians, researchers, and engineers who work with Optomec Aerosol Jet Printers. It allows you to upload a design file *before* printing to find potential issues like sharp corners, non-tangential curves, and arcs that would exceed a given G-force limit.

**[Live Application URL]([https://prg-web-analyzer.streamlit.app](https://prg-web-analyzer-vw43e8ieuq532g6xqfd44t.streamlit.app/))**

---

## 📸 Quick Demo

![Screenshot of the Analyzer in action]([https://i.imgur.com/YOUR_IMAGE_LINK.png](https://i.imgur.com/JnmREBB.jpeg))  

---

## ✨ Core Features

* **📈 Max Speed Calculation:** Determines the *maximum safe process speed* (mm/s) based on the tightest arc in the design and a user-defined G-Factor limit.
* **⚠️ Geometric Stress Analysis:** Automatically detects and flags common design flaws that cause print failures, including:
    * **Line-to-Line:** Sharp turns (> 1.0°) between straight segments.
    * **Line-to-Arc:** Non-tangential transitions where a line meets a curve.
    * **Arc-to-Arc:** Abrupt, non-collinear changes between two connected arcs.
* **📹 Toolpath Animation:** Renders a full video animation of the printer's path, color-coding printing moves (red) vs. rapid moves (blue).
* **📝 Annotated File Generation:** Provides a "Download" button for a new `_annotated.prg` file, with warning and info comments added directly into the original code at the exact line where the issue occurs.
* **🌎 Web-Based & Zero-Install:** Runs entirely in a web browser. No Python, no installations, no setup needed. Works on any OS (Windows, macOS, Linux).

---

## 🛠️ How to Use

1.  **Open the Web App:** Navigate to the [live application URL]([https://prg-web-analyzer.streamlit.app](https://prg-web-analyzer-vw43e8ieuq532g6xqfd44t.streamlit.app/)).
2.  **Upload File:** Click the "Upload your .prg file" button in the sidebar and select your file.
3.  **Set G-Factor:** In the sidebar, enter the desired acceleration limit as a factor of g=9800 mm/s^2 (e.g., `0.5`).
4.  **Run Analysis:** Click the "Run Analysis" button.
5.  **Review Results:**
    * The **Analysis Report** will appear on the main page.
    * The **Toolpath Animation** video will be rendered below the report.
    * A **Download Annotated .prg File** button will appear.

---

## 🔒 Data Privacy, Security, and Hosting Model

This section provides a transparent overview of how the application is hosted and how it handles user data.

### Hosting
The application is hosted on **Streamlit Community Cloud**, a free, public platform. The application's source code, which is hosted in this **public GitHub repository**, is read by Streamlit's servers to build and run the app.

### Data Flow and Ephemeral Storage
This is the most critical point regarding data privacy:

1.  **File Upload:** When you upload a `.prg` file, it is sent to a temporary, isolated server instance (a "container") running the Streamlit app.
2.  **In-Memory Processing:** The file is held in the server's temporary storage *only for the duration of your active session*. The Python script reads the file, performs all calculations, and generates the report and video in memory.
3.  **Data Destruction:** When you close your browser tab, or after a short period of inactivity, your session ends. The server container running your session is **automatically destroyed**, and **all temporary files and in-memory data are permanently wiped**.

**This application *never* saves your uploaded `.prg` files, reports, or videos to a permanent database.** The entire process is ephemeral (temporary) and designed for "in-and-out" analysis.

### What Data *is* Stored?
The *only* piece of data that is saved is the last-used **G-Factor**. This non-sensitive, operational parameter is saved in the `analyzer_config.ini` file, which is part of the public GitHub repository, to provide a convenient default value for all users. No user data, filenames, or design data are ever written to this file.

### A Note for LTI/KIT IT Staff
This application is built for convenience using a free, public hosting model. This model has two key implications:
1.  **Public Access:** The app URL is public. Anyone with the link can access and use the tool.
2.  **Data Transfer:** Although ephemeral, the uploaded `.prg` file *is* temporarily transferred to and processed on Streamlit's external servers (which are likely outside the EU).

If these `.prg` files are considered highly confidential or proprietary, and their transfer to a third-party server (even temporarily) violates institute policy, **this public app should not be used.**

You have two excellent, more secure alternatives:

1.  **Internal Hosting (Recommended):** The entire application is a simple Python script (`streamlit_app.py`). Your IT department can run this script on an **internal institute server**. This would make the app accessible *only* via the KIT intranet, and no data would ever leave the institute's network. This is the most secure solution.
2.  **Private Hosting:** The GitHub repository can be made private, and the app can be deployed on a paid, private platform (like Streamlit for Teams, Snowflake, or a cloud provider like AWS/Azure), which allows for password protection and better compliance.

---

## 🤖 Technical Breakdown

This application is built entirely in Python and leverages the following key libraries:

* **Streamlit:** For building the interactive web GUI.
* **Matplotlib:** For generating the animation frames from the toolpath data.
* **NumPy:** For performing the vector math and geometry calculations for the stress analysis.
* **FFmpeg:** The underlying video engine (installed on the server via `packages.txt`) that Matplotlib uses to render the animation as an `.mp4` file.

The analysis is performed using a custom parser that reads the `.prg` file line-by-line and converts it into a structured list of movement segments (Lines, Arcs, and PTP moves). Vector math is then used to analyze the tangents and curvature at each segment's junction.

---

## 🧑‍💻 Author

* **[Suraj Ramesh Iyer]** - *Initial Work & Development* - [https://github.com/iyer7]
