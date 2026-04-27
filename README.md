# IntelliPlan-3D  
AI-Based 2D-3D Floor Plan Recommendation System with Augmented Reality

---

## Overview

IntelliPlan-3D is an intelligent system that automates residential floor plan design using Artificial Intelligence. It allows users to generate optimized 2D and 3D floor plans based on simple inputs such as plot size, number of rooms, and user preferences. The system removes the need for manual drafting and reduces dependency on professional architects for basic planning. It focuses on efficient space utilization, logical room placement, and real-world usability. It also integrates Augmented Reality to help users visualize generated floor plans in a more interactive way.

---

## Key Features

- Automatic 2D floor plan generation
- 3D visualization of layouts
- Augmented Reality based real-world preview
- Multiple layout recommendations for same input
- Smart space optimization using AI algorithms
- User-friendly interface for non-technical users
- Custom preferences support (room arrangement, Vastu, etc.)
- Fast and cost-effective solution

---

## Motivation

- Traditional floor planning is time-consuming and expensive
- Requires professional knowledge and repeated revisions
- Beginners struggle with space planning and layout design
- Increasing demand for efficient housing solutions

IntelliPlan-3D solves these problems by:

- Automating the design process
- Reducing errors and manual effort
- Providing multiple design options
- Making planning accessible to everyone

---

## Objectives

- Design an AI-based system for floor plan generation
- Provide both 2D and 3D outputs
- Integrate AR for better visualization
- Ensure optimal space utilization
- Build a simple and interactive user interface

---

## System Architecture

<img width="1818" height="1088" alt="Image" src="https://github.com/user-attachments/assets/d39c2888-a0fd-45fc-9942-5b3c77a015c9" />


---

## Project Structure

```
IntelliPlan-3D/
│
├── backend/
│   ├── app.py                # Main backend application
│   ├── config.py             # Configuration settings
│   ├── analytics.py          # Analysis and evaluation logic
│   ├── check_accuracy.py     # Accuracy testing module
│   ├── requirements.txt      # Backend dependencies
│   ├── .env.example          # Environment variables template
│   │
│   ├── ga_engine/            # Genetic Algorithm logic
│   ├── vastu_engine/         # Vastu rule processing
│   ├── geometry/             # Layout calculations and geometry logic
│   ├── services/             # Core service layer
│   ├── utils/                # Utility functions
│   │
│   ├── test_ga_engine.py     # GA engine tests
│   ├── test_geometry.py      # Geometry tests
│   └── test_vastu_engine.py  # Vastu engine tests
│
├── frontend/
│   ├── index.html            # Main UI page
│   ├── styles.css            # Styling
│   ├── script.js             # Frontend logic
│   ├── ar.js                 # Augmented Reality features
│   └── pdf.js                # PDF generation
│
├── README.md                 # Project documentation
└── .gitignore                # Git ignore rules
```

---
## Tech Stack

Programming Language: Python is used for backend development and algorithm implementation.

Backend Framework: FastAPI is used to handle API requests and connect the frontend with the backend.

Frontend Technologies: HTML, CSS, and JavaScript are used to design the user interface and manage user interaction.

Development Environment: Visual Studio Code is used for coding, debugging, and overall project management.

Libraries: NumPy and Matplotlib are used for data processing and visualization tasks.

Visualization Tools: 2D graphics and 3D rendering tools are used to display floor plans in visual formats.

Version Control: Git is used for code management and tracking changes during development.

Operating System: Windows is used as the platform for development and execution.

Browser: Google Chrome is used to run and test the web application.

---

## How It Works

1. User enters input details  
2. System processes inputs using AI algorithms  
3. Generates multiple 2D layouts  
4. Converts selected layout into 3D model  
5. Displays model in AR for real-world view  

---

## Advantages

- Saves time and cost  
- Reduces human errors  
- Provides multiple design options  
- Easy to use for beginners  
- Improves decision making  

---

## Future Scope

1. Support for complex plot shapes  
2. Advanced customization and user control  
3. Improved AI and optimization  
4. Integration of construction rules and planning  
5. Enhanced visualization and user experience  

---

## Team Members

- Mayur Bhong  
- Kartik Mathpati 
- Mansi Bang

---

## Acknowledgment

We thank our faculty and mentors for guidance and support in completing this project.
