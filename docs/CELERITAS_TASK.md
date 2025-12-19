# Overview
Build a web service that accepts PDF files and answers questions using content from the most relevant PDF.

# Requirements
Upload one or more PDF files
Accept natural language questions via API
Use OpenAI API to extract answers from PDFs
Return answers with PDF source citation

Your system must track all interactions:
Store every question asked with timestamp
Store which PDF(s) was used to answer
Store the actual answer returned
Store user feedback (thumbs up/down) on answers
Store response time/performance metrics

# Analytics Endpoint that answers
"Which documents are queried most frequently?"
"What questions are asked most often?"
"How many queries were answered from each PDF this week?"

# Technical Constraints
Use OpenAI API (your choice: Vision, embeddings etc.)
Python web framework (Flask/FastAPI recommended)
Store uploaded PDFs (local filesystem acceptable)

# Sample Data
PDFs provided:
- Introduction_to_climate_change (1).pdf
- H1-DME-pp (3).pdf

# Test questions:
"What is causing global warming?"
"Summarize the impacts of climate change"
"What dental appliances are covered by Harvard Pilgrim?"
"What is the code for a CPAP water chamber?"

# Key Deliverables
Modular and maintainable codebase following best practices
Clear separation of concerns
Design and architecture documents

