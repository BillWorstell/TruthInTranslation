# Truth In Translation

**(Pre‐Release / Private Repository)**

Welcome to **Truth In Translation**, a bilingual folklore reader and AI‐assisted language learning application. This project focuses on **Akan–English** folklore texts, leveraging both **AI** and **human translations** to ensure cultural fidelity and transparent comparison. Our goal is to preserve **oral traditions** while providing educational and linguistic insights for learners, educators, and researchers.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture & Workflow](#architecture--workflow)
- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [Project Status & Roadmap](#project-status--roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

**Truth In Translation** aims to:

- Provide **parallel** (side‐by‐side) **Akan–English** texts from folklore sources, preserving cultural nuance.  
- Offer **AI model comparison** (e.g., GPT‐4 vs. GPT‐3.5) plus **human reference translations**.  
- Feature **interactive** reading modes with dictionary lookups and **reading‐level** adaptations.  
- Enable offline or low‐resource usage by **pre‐generating** translations into SQLite/Excel databases.

This repository houses code, documentation, and sample workflows for generating bilingual corpora, applying AI translations, and displaying them interactively (via Streamlit or notebook interfaces).

---

## Key Features

1. **Line‐by‐Line Alignment**  
   - Segmentation of Akan and English sentences into aligned rows.  
   - Output to 2‐column Excel sheets for easy editing or revision.

2. **AI Translation & Parsing**  
   - Use of [OpenAI’s API](https://platform.openai.com/docs/introduction) (GPT‐4, GPT‐3.5, etc.) for automated translations.  
   - Automatic breakdown into **Literal** / **Faithful** translations and **Footnotes**.

3. **Comparison Against Human Expert Translations**  
   - Systematic side‐by‐side viewing of **AI** vs. **human** outputs with commentary on fidelity and cultural context.

4. **Dictionary & Linguistic Data**  
   - Storage of Akan words, parts of speech, morphological info in a **SQLite** database for quick lookups.  
   - Inline or tooltip dictionary references in the user interface.

5. **Offline / Low‐Resource Operation**  
   - Once translations are generated, the data can be **frozen** into Excel/SQLite files.  
   - The interactive interface (e.g., Streamlit) can run locally without active AI calls.

-
